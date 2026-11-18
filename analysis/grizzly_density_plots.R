library(ggplot2)
library(patchwork)

## ---- Settings to edit ----
forest_rng <- c(-2, 2)   # use c(0, 1) if forest entered as a proportion
z_unburned <- 0.5        # standardized fire value of never-burned cells
fire_min   <- -4         # most recent burn, in SD units

## ---- Posterior quantiles: 2.5, 25, 50, 75, 97.5% ----
q <- rbind(
  c(-0.0009136,  0,         0,         0,         0.013332),
  c(-1.4070036, -1.333323, -1.295326, -1.259453, -1.186216),
  c( 1.2010558,  1.350420,  1.431731,  1.532498,  1.696142),
  c( 0,          0,         0,         0,         0.015045),
  c( 1.1645688,  1.472806,  1.669261,  1.861279,  2.146065),
  c( 0.1024200,  0.186695,  0.235589,  0.291826,  0.399218),
  c(-2.0445426, -1.736259, -1.541636, -1.373083, -1.046734),
  c(-0.2801733,  0,         0,         0.239519,  0.696856),
  c(-0.3702942, -0.322245, -0.297890, -0.272554, -0.227533),
  c(-0.3871070, -0.347947, -0.326687, -0.306225, -0.269199),
  c(-0.0885072, -0.073246, -0.064500, -0.055953, -0.040951),
  c( 0.2144915,  0.259517,  0.282931,  0.306896,  0.353504),
  c(-0.1427947, -0.026176,  0,         0,         0.010977))
colnames(q) <- c("lo", "q25", "med", "q75", "hi")

post <- data.frame(
  term = c("Years since fire", "Protected (IUCN)", "% forest",
           "Years since fire^2", "NPP x % forest", "Distance to roads",
           "NPP", "Historical refugia", "Grizzly range",
           "Years since fire", "Years since fire^2", "Protected (IUCN)", "NPP"),
  part = rep(c("Density", "Sigma"), c(9, 4)), q)
post$support <- ifelse(post$med == 0, "Often excluded", "Consistently included")
post$term <- factor(post$term, levels = rev(unique(post$term)))

## ---- A. Coefficients ----
pA <- ggplot(post, aes(y = term, colour = support)) +
  geom_vline(xintercept = 0, linetype = 2) +
  geom_linerange(aes(xmin = lo, xmax = hi)) +
  geom_linerange(aes(xmin = q25, xmax = q75), linewidth = 2) +
  geom_point(aes(x = med), colour = "black", size = 2) +
  facet_wrap(~part, scales = "free") +
  labs(x = "Coefficient (median, 50% and 95% CrI)", y = NULL, colour = NULL,
       title = "A. Posterior coefficients") +
  theme_bw() + theme(legend.position = "bottom")

## ---- B. Density multipliers for simple contrasts ----
both <- q[2, "med"] + q[9, "med"]   # interval needs MCMC samples
mult <- data.frame(
  contrast = c("Inside protected land", "Inside grizzly range",
               "Protected + grizzly range", "Inside historical refugia",
               "+1 SD distance from roads"),
  est = exp(c(q[2, "med"], q[9, "med"], both, q[8, "med"], q[6, "med"])),
  lo  = exp(c(q[2, "lo"],  q[9, "lo"],  both, q[8, "lo"],  q[6, "lo"])),
  hi  = exp(c(q[2, "hi"],  q[9, "hi"],  both, q[8, "hi"],  q[6, "hi"])))
pB <- ggplot(mult, aes(est, reorder(contrast, est))) +
  geom_vline(xintercept = 1, linetype = 2) +
  geom_pointrange(aes(xmin = lo, xmax = hi)) +
  scale_x_log10() +
  labs(x = "Density multiplier", y = NULL, title = "B. Density contrasts") +
  theme_bw()

## ---- C. Forest x NPP surface ----
g <- expand.grid(forest = seq(forest_rng[1], forest_rng[2], length.out = 100),
                 npp = seq(-2, 2, length.out = 100))
g$relD <- exp(q[3, "med"] * g$forest + q[7, "med"] * g$npp +
              q[5, "med"] * g$forest * g$npp)
pC <- ggplot(g, aes(forest, npp)) +
  geom_raster(aes(fill = relD)) +
  geom_contour(aes(z = log10(relD)), colour = "white", alpha = 0.5) +
  scale_fill_viridis_c(trans = "log10", name = "Relative\ndensity") +
  labs(x = "% forest (model scale)", y = "NPP (SD)",
       title = "C. Forest x NPP") +
  theme_bw()

## ---- D. Sigma vs years since fire ----
s <- expand.grid(fire = seq(fire_min, z_unburned, length.out = 200),
                 prot = c("Unprotected", "Protected"))
s$relSig <- exp(q[10, "med"] * s$fire + q[11, "med"] * s$fire^2 +
                q[12, "med"] * (s$prot == "Protected"))
pD <- ggplot(s, aes(fire, relSig, colour = prot)) +
  geom_line(linewidth = 1) +
  geom_vline(xintercept = z_unburned, linetype = 3) +
  labs(x = "Years since fire (SD; dotted line = never burned)",
       y = "Relative sigma", colour = NULL, title = "D. Movement scale") +
  theme_bw()

## ---- E. Distance to roads ----
r <- data.frame(x = seq(-2, 2, length.out = 100))
r$est <- exp(q[6, "med"] * r$x)
r$lo  <- pmin(exp(q[6, "lo"] * r$x), exp(q[6, "hi"] * r$x))
r$hi  <- pmax(exp(q[6, "lo"] * r$x), exp(q[6, "hi"] * r$x))
pE <- ggplot(r, aes(x, est)) +
  geom_ribbon(aes(ymin = lo, ymax = hi), alpha = 0.3) +
  geom_line(linewidth = 1) +
  labs(x = "Distance to roads (SD)", y = "Relative density",
       title = "E. Roads") +
  theme_bw()

fig <- pA / (pB | pE) / (pC | pD)
fig
ggsave("grizzly_density_plots.png", fig, width = 11, height = 13, dpi = 150)

## ---- With the MCMC samples (matrix `samples`) ----
# Exact inclusion probabilities:
# colMeans(samples[, grep("^z(beta|sig)\\[", colnames(samples))] != 0)
# NPP slope across forest, with a proper credible band:
# f <- seq(forest_rng[1], forest_rng[2], length.out = 50)
# slope <- sapply(f, function(x)
#   quantile(samples[, "zbeta[7]"] + samples[, "zbeta[5]"] * x, c(.025, .5, .975)))
