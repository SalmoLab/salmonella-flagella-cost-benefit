# Supplementary Table X. Parameters of the active-particle motility simulation

Every parameter carries one of five sources. **Measured** values come
from the paired experimental units of this study. **Fitted** values are
scaled so the model persistence time equals the measured persistence
time. **Literature** values are taken from a published measurement in
another organism. **Literature-scaled** values have no published
absolute value; only their ratio between strains is set by a published
measurement. **Nominal** values are defaults of the published
simulation code and are not derived from our data.

| Parameter | Symbol | Unit | PproA (liquid) | WT (liquid) | PproB (liquid) | PproA (agarose) | WT (agarose) | PproB (agarose) | Source |
|---|---|---|---|---|---|---|---|---|---|
| motile_fraction | f_motile | - | 0.635 | 0.801 | 0.86 | 0.42 | 0.732 | 0.748 | Measured |
| run_speed_um_s | v | um s^-1 | 19.9 | 27.6 | 32 | 15.4 | 23.2 | 28.6 | Measured |
| rotational_diffusion_rad2_s | D_theta | rad^2 s^-1 | 6.15 | 4.3 | 4.23 | 8.56 | 5.86 | 5.16 | Fitted |
| reorientation_rate_s | lambda | s^-1 | 6.21 | 6.62 | 5.09 | 13.2 | 7.81 | 6.82 | Fitted |
| turn_angle_sd_rad | sigma | rad | 1.25 | 1.25 | 1.25 | 1.25 | 1.25 | 1.25 | Literature |
| passive_diffusion_um2_s | D_t | um^2 s^-1 | 0.35 | 0.35 | 0.35 | 0.35 | 0.35 | 0.35 | Nominal |
| stall_probability | p_stall | - | 0 | 0 | 0 | 0.21 | 0.177 | 0.123 | Literature-scaled |
| stall_mean_duration_s | t_stall | s | 0.05 | 0.05 | 0.05 | 0.949 | 0.949 | 0.949 | Nominal |
| run_translational_scale | c_run | - | 0.12 | 0.12 | 0.12 | 0.12 | 0.12 | 0.12 | Nominal |
| stall_translational_scale | c_stall | - | 0.2 | 0.2 | 0.2 | 0.2 | 0.2 | 0.2 | Nominal |
| stall_slide_fraction | c_slide | - | 0.28 | 0.28 | 0.28 | 0.28 | 0.28 | 0.28 | Nominal |
| stall_rotational_diffusion_scale | c_rot | - | 1.8 | 1.8 | 1.8 | 1.8 | 1.8 | 1.8 | Nominal |

## Notes

- **motile_fraction** (Measured). Per-strain, per-medium fraction of swimming cells (this study).
- **run_speed_um_s** (Measured). Per-strain, per-medium mean run speed (this study).
- **rotational_diffusion_rad2_s** (Fitted). Effective heading-decorrelation rate during runs. Not the rotational diffusion of the cell body, which is 0.057 rad^2 s^-1 for swimming E. coli (Drescher et al., 2011).
- **reorientation_rate_s** (Fitted). Scaled with D_theta by one factor so the model persistence time equals the measured one; the delivered ratio is kept.
- **turn_angle_sd_rad** (Literature). One global value for all six rows. Set so the mean turn magnitude sigma * sqrt(2 / pi) equals the 57 deg mean turn angle of Taute et al., 2015 (n = 8058 turns, E. coli AW405; doi:10.1038/ncomms9776, PMID 26522289). Taute et al. tracked in three dimensions; this simulator is two-dimensional, so only the mean magnitude is matched, not the forward-skewed shape of the measured distribution.
- **passive_diffusion_um2_s** (Nominal). Nominal value of the published code. Agrees within 3 % with the Stokes-Einstein value for a 2.0 x 0.8 um cell at 20 degC.
- **stall_probability** (Literature-scaled). Per-contact-event probability: the chance that one encounter with one obstacle ends in a stall rather than a tangential slide. It is drawn once, on the step where the cell first overlaps a disk it was not already touching, so the value is a property of the model and not of the time step. This is the same quantity Grognot et al. measured, a stall frequency per contact. No primary measurement gives its absolute value. Its ratio between strains is anchored: it falls with the mean hook number per cell as N^-0.704 (PproA 2.085, WT 2.666, PproB 4.432), normalised so the mean over the three strains is unchanged. The exponent sets the ratio between the least and the most flagellated strain to the 1.7 +/- 0.2 stall-frequency ratio measured in 0.25 % agar by Grognot et al., 2023 (doi:10.1073/pnas.2301873120, PMID 37579142). That study varied a second flagellar system in Vibrio alginolyticus, not the flagella count, so the mapping onto our hook numbers is an assumption. Zero in liquid.
- **stall_mean_duration_s** (Nominal). One global value for the three agarose rows. Grognot et al., 2023 found the flagella effect on stall duration significant only at 0.16 % agar, not at the 0.25 % that matches our condition, so a per-strain duration is not supported and one value is what the evidence carries. The absolute value has no source. Reported trapping times in gels span 0.4 to 40 s (Bhattacharjee and Datta, 2019) and average 2.1 to 3.6 s (Datta et al., 2025), so this value sits below the published means. Those distributions are power-law; the model draws an exponential. The liquid rows keep the nominal 0.05 s of the published code, which never fires because their stall probability is zero.
- **run_translational_scale** (Nominal). Global model constant, one value for all six rows. It multiplies the passive diffusion coefficient D_t to set the translational noise of a cell that is running. It has no source: it is a default of the published code and no measurement in this study or in the literature sets it.
- **stall_translational_scale** (Nominal). Global model constant, one value for all six rows. It multiplies D_t to set the translational noise of a cell that is stalled against an obstacle. It has no source. Until this revision it was written as a bare number inside the integration loop, so it appeared in no config file and no table; it now carries the config key noise.stall_translational_scale.
- **stall_slide_fraction** (Nominal). Global model constant, one value for all six rows. When a cell meets an obstacle and does not stall, it keeps this fraction of the tangential part of its step and slides along the surface. It has no source.
- **stall_rotational_diffusion_scale** (Nominal). Global model constant, one value for all six rows. It multiplies the rotational diffusion rate D_theta while a cell is stalled, so a stalled cell reorients faster than a running one. It has no source.

- **Derived persistence time** tau (s), not an independent parameter: PproA liquid 0.105; WT liquid 0.127; PproB liquid 0.143; PproA agarose 0.064; WT agarose 0.099; PproB agarose 0.113.
  tau = 1 / (D_theta + lambda * (1 - exp(-sigma^2 / 2))).
- **Reorientation is instantaneous.** The persistence relation above carries no
  duration term, so a reorientation dwell would simulate a different model from the
  one the parameters are fitted to. The corrected dynamics apply the heading kick at
  the transition and the cell keeps swimming, so `reorientation_duration_s` is not a
  parameter of the model and no longer appears in this table. The measured tumble
  duration of *E. coli*, 0.19 s (Taute et al., 2015), cannot simply be substituted: at
  the fitted reorientation rates it would put cells in a non-swimming state 49 % to 71 %
  of the time and remove most directed motion. A model with a real tumble duration
  needs the persistence relation refitted with a duration term.
- **The four noise constants have no source.** They are defaults of the published
  code. They are listed here because they change the physics, and because they were
  absent from every table before this revision. They also order translational noise
  the wrong way round: a running cell gets 0.12 of the passive diffusion
  coefficient, a stalled cell 0.20 and a non-motile cell 1.00, so a swimming cell
  diffuses about eight times less than a stopped one. The size of that defect was
  measured against a physically ordered alternative in which every state diffuses at
  the full passive rate, 100 seeds per group, paired by seed. The plotted observable
  barely moves: net displacement changes by at most 3.5 % (WT agarose, 95 % CI
  [-7.1, +0.2] %), and no agarose interval excludes zero. Effective diffusivity in
  agarose moves more, by -6.2 % (PproB, 95 % CI [-8.0, -4.5] %), because larger
  translational noise drives cells into obstacles more often and raises the stall
  occupancy. The constants are therefore declared and kept, not changed; the agarose
  effective-diffusivity sensitivity is stated as a limitation. See
  `motility_parameter_sources.md` for the full measurement.
- **Integration.** Time step 0.0025 s. A 100-seed convergence test accepts every step whose group mean net displacement stays within 5% of the mean of the two finest steps tested, 0.000625, 0.00125 s. The largest accepted step is 0.05 s; the panels run at 0.0025 s, which is finer and therefore inside the tolerance, where the largest group deviation is 2.0%. The stall probability is drawn once per contact event, so stall occupancy converges with the step. Contour path length does not converge at all and is not reported. The quantitative panels run in a 1776 x 1152 um box, enlarged so the reflecting walls do not compress the strain ratios; the obstacle count scales with box area and the realised obstacle area fraction is 0.187.
- Full bibliographic records are in `motility_parameter_sources.md`.
