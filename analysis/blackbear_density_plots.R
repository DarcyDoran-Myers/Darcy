## Female black bear density & sigma (SCR, NW quadrant of species range)
## Figure 1 (main): effects on the density / sigma scale
## Figure S1 (supplement): posterior coefficients
library(ggplot2)
library(patchwork)

## ---- Settings to edit ----
forest_rng <- c(-2, 2)   # restrict to the observed range of % forest (model scale)
npp_levels <- c(-1, 0, 1) # NPP values (SD) for the forest x NPP lines
z_unburned <- 0.5        # standardized fire value of never-burned cells
fire_min   <- -4         # most recent burn, in SD units

## ---- Posterior quantiles: 2.5, 25, 50, 75, 97.5% ----
q <- rbind(
  c(-0.0009136,  0,         0,         0,         0.013332),  # zbeta[1] fire
  c(-1.4070036, -1.333323, -1.295326, -1.259453, -1.186216),  # zbeta[2] protected
  c( 1.2010558,  1.350420,  1.431731,  1.532498,  1.696142),  # zbeta[3] forest
  c( 0,          0,         0,         0,         0.015045),  # zbeta[4] fire^2
  c( 1.1645688,  1.472806,  1.669261,  1.861279,  2.146065),  # zbeta[5] NPP x forest
  c( 0.1024200,  0.186695,  0.235589,  0.291826,  0.399218),  # zbeta[6] roads
  c(-2.0445426, -1.736259, -1.541636, -1.373083, -1.046734),  # zbeta[7] NPP
  c(-0.2801733,  0,         0,         0.239519,  0.696856),  # zbeta[8] historical
  c(-0.3702942, -0.322245, -0.297890, -0.272554, -0.227533),  # zbeta[9] grizzlies
  c(-0.3871070, -0.347947, -0.326687, -0.306225, -0.269199),  # zsig[1] fire
  c(-0.0885072, -0.073246, -0.064500, -0.055953, -0.040951),  # zsig[2] fire^2
  c( 0.2144915,  0.259517,  0.282931,  0.306896,  0.353504),  # zsig[3] protected
  c(-0.1427947, -0.026176,  0,         0,         0.010977))  # zsig[4] NPP
colnames(q) <- c("lo", "q25", "med", "q75", "hi")

th  <- theme_bw(base_size = 11) +
  theme(panel.grid.minor = element_blank(), plot.title = element_text(face = "bold"))
pal <- c(Unprotected = "#7a7a7a", Protected = "#1b7837")   # panel D
npp_pal <- c("#d8b365", "#5ab4ac", "#01665e")              # panel C (low -> high NPP)

## =====================================================================
## Figure 1
## =====================================================================

## ---- A. Categorical contrasts (density multipliers) ----
mult <- data.frame(
  contrast = c("Protected area (IUCN)", "Inside grizzly range",
               "Historical refugia", "+1 SD farther from roads"),
  row = c(2, 9, 8, 6))
mult$est <- exp(q[mult$row, "med"])
mult$lo  <- exp(q[mult$row, "lo"])
mult$hi  <- exp(q[mult$row, "hi"])
mult$contrast <- factor(mult$contrast, levels = rev(mult$contrast))
pA <- ggplot(mult, aes(est, contrast)) +
  geom_vline(xintercept = 1, linetype = 2, colour = "grey50") +
  geom_pointrange(aes(xmin = lo, xmax = hi)) +
  geom_text(aes(label = sprintf("%.2f×", est)), vjust = -0.9, size = 3.2) +
  scale_x_log10(breaks = c(0.25, 0.5, 1, 2)) +
  labs(x = "Density multiplier (log scale)", y = NULL,
       title = "A. Where density is higher or lower") + th

## ---- B. Distance to roads ----
r <- data.frame(x = seq(-2, 2, length.out = 100))
r$est <- exp(q[6, "med"] * r$x)
r$lo  <- pmin(exp(q[6, "lo"] * r$x), exp(q[6, "hi"] * r$x))
r$hi  <- pmax(exp(q[6, "lo"] * r$x), exp(q[6, "hi"] * r$x))
pB <- ggplot(r, aes(x, est)) +
  geom_hline(yintercept = 1, linetype = 2, colour = "grey50") +
  geom_ribbon(aes(ymin = lo, ymax = hi), alpha = 0.25) +
  geom_line(linewidth = 1) +
  labs(x = "Distance to roads (SD)", y = "Relative density",
       title = "B. Roads") + th

## ---- C. Forest x NPP (conditional lines instead of a surface) ----
g <- expand.grid(forest = seq(forest_rng[1], forest_rng[2], length.out = 100),
                 npp = npp_levels)
g$relD <- exp(q[3, "med"] * g$forest + q[7, "med"] * g$npp +
              q[5, "med"] * g$forest * g$npp)
g$npp_lab <- factor(sprintf("NPP %+d SD", g$npp), levels = sprintf("NPP %+d SD", npp_levels))
pC <- ggplot(g, aes(forest, relD, colour = npp_lab)) +
  geom_hline(yintercept = 1, linetype = 2, colour = "grey50") +
  geom_line(linewidth = 1) +
  scale_y_log10() +
  scale_colour_manual(values = npp_pal) +
  labs(x = "% forest (SD)", y = "Relative density (log scale)", colour = NULL,
       title = "C. Forest effect depends on NPP") +
  th + theme(legend.position = c(0.98, 0.02), legend.justification = c(1, 0),
             legend.background = element_blank())

## ---- D. Sigma vs time since fire ----
s <- expand.grid(fire = seq(fire_min, z_unburned, length.out = 200),
                 prot = c("Unprotected", "Protected"))
s$relSig <- exp(q[10, "med"] * s$fire + q[11, "med"] * s$fire^2 +
                q[12, "med"] * (s$prot == "Protected"))
pD <- ggplot(s, aes(fire, relSig, colour = prot)) +
  geom_line(linewidth = 1) +
  geom_vline(xintercept = z_unburned, linetype = 3) +
  annotate("text", x = z_unburned, y = max(s$relSig), label = "never\nburned",
           hjust = 1.1, vjust = 1, size = 3) +
  scale_colour_manual(values = pal) +
  labs(x = "Years since fire (SD; recent burn → older)",
       y = "Relative sigma (space use)", colour = NULL,
       title = "D. Space use peaks at intermediate fire age") +
  th + theme(legend.position = c(0.02, 0.02), legend.justification = c(0, 0),
             legend.background = element_blank())

fig1 <- (pA | pB) / (pC | pD) +
  plot_annotation(
    title = "Female black bears, NW quadrant of the species range",
    subtitle = "Posterior medians with 95% CrI; curves in C and D are medians only",
    theme = theme(plot.title = element_text(face = "bold", size = 14)))
ggsave("blackbear_fig1_effects.png", fig1, width = 11, height = 8.5, dpi = 150)

## =====================================================================
## Figure S1: coefficients
## =====================================================================
post <- data.frame(
  term = c("Years since fire", "Protected (IUCN)", "% forest",
           "Years since fire²", "NPP × % forest", "Distance to roads",
           "NPP", "Historical refugia", "Grizzly range",
           "Years since fire", "Years since fire²", "Protected (IUCN)", "NPP"),
  part = rep(c("Density (β)", "Sigma (σ)"), c(9, 4)), q)
post$support <- ifelse(post$med == 0, "Median = 0 (often excluded)", "Consistently included")
post$term <- factor(post$term, levels = rev(unique(post$term)))
figS1 <- ggplot(post, aes(y = term, colour = support)) +
  geom_vline(xintercept = 0, linetype = 2, colour = "grey50") +
  geom_linerange(aes(xmin = lo, xmax = hi)) +
  geom_linerange(aes(xmin = q25, xmax = q75), linewidth = 2) +
  geom_point(aes(x = med), colour = "black", size = 2) +
  facet_wrap(~part, scales = "free") +
  scale_colour_manual(values = c("#2166ac", "#b2182b")) +
  labs(x = "Standardized coefficient (median, 50% and 95% CrI)", y = NULL,
       colour = NULL, title = "Posterior coefficients") +
  th + theme(legend.position = "bottom")
ggsave("blackbear_figS1_coefficients.png", figS1, width = 10, height = 5, dpi = 150)

## ---- With the MCMC samples (matrix `samples`) ----
# Inclusion probabilities (label Fig S1 with these instead of median == 0):
# colMeans(samples[, grep("^z(beta|sig)\\[", colnames(samples))] != 0)
# Credible bands for panel C (repeat for each NPP level):
# band <- sapply(f, function(x) quantile(exp(samples[,"zbeta[3]"]*x +
#   samples[,"zbeta[7]"]*n + samples[,"zbeta[5]"]*x*n), c(.025,.5,.975)))
# Same idea for panel D using zsig[1], zsig[2], zsig[3].
