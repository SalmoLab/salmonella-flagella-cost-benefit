# Flagella number and swimming behaviour — literature check

Status: literature survey for the revision, 13 August 2026.
Purpose: decide whether a run-and-tumble model parameter can be tied to the
measured flagella number per cell, instead of being fitted per strain.

## How to read this file

Every number below comes from a source that I opened and read. Where I could
not read the value, the entry says **not verified**. Nothing comes from memory.
Search used PubMed, PubMed Central full text, and publisher pages for the
physics journals. Some literature is retrieved through PubMed and PubMed
Central; DOIs are given for every citation.

Values that I calculated from our own measurements are marked "derived here".

## Our own numbers, for reference

Mean hooks per cell: PproA 2.09, WT 2.67, PproB 4.43 (29,789 cells).
Fraction of cells with at least one hook: PproA 0.771, WT 0.889, PproB 0.877.
Mean liquid swimming speed: PproA 19.9, WT 27.6, PproB 32.0 um/s.

## Organism warning — read this first

No primary study measures how flagella number changes swimming behaviour in
*Salmonella enterica* serovar Typhimurium. I searched and found none. The
direct measurements come from *Escherichia coli* and from *Bacillus subtilis*.

The flagella-number ranges differ strongly:

| source | organism | flagella per cell |
|---|---|---|
| this study | *S.* Typhimurium | 2.09 to 4.43 (mean hooks) |
| Lisevich et al. 2025 | *E. coli* | 0 to about 10 |
| Honda et al. 2022 | *E. coli* | titrated, mean 0 to about 5 |
| Turner et al. 2000 | *E. coli* | 3.37 ± 1.59 |
| Mears et al. 2014 | *E. coli* | 1 to more than 10 |
| Najafi et al. 2018 | *B. subtilis* | 9 ± 2, 26 ± 6, 41 ± 6 |

Our range sits at the low end. The *B. subtilis* work sits far above it. Use
*B. subtilis* for the direction of an effect, never for its size.

---

## 1. Swimming speed versus flagella number

**Answer: speed rises with flagella number up to about five flagella per cell,
then saturates. No study fits a power law, so no measured `alpha` exists.**

### The one direct, on-range measurement

**Lisevich et al. 2025**, *E. coli* MG1655 carrying a P*tac*-*flhDC*
construct, plus 24 natural ECOR isolates. Flagella counted for 106 cells in
total, flagellated and non-flagellated. The paper states:

> "cell swimming velocity only increases as a function of flagellar gene
> expression until the number of flagella reaches ~5, which corresponds to the
> number observed in the wild-type MG1655 cells, but saturates above this
> level."

This is the closest analogue to our design. They tune a flagellar promoter,
we tune a flagellar promoter. Their rising regime, 0 to about 5 flagella per
cell, contains our whole range (2.09 to 4.43).
Caveat: promoter titration changes filament length as well as filament number.
The paper reports that flagellar length falls below about two flagella per
cell. Speed and number therefore co-vary with expression, exactly as in our
strains. The study does not isolate number.
Lisevich I, Colin R, Yang HY, Ni B, Sourjik V. Physics of swimming and its
fitness cost determine strategies of bacterial investment in flagellar
motility. Nat Commun 2025;16:1731. DOI 10.1038/s41467-025-56980-x.
PMID 39966405.

### Measurements that report no dependence

**Najafi et al. 2018**, *B. subtilis*, more than 2500 trajectories, quasi-2D
chamber. Flagella per cell 9 ± 2, 26 ± 6, 41 ± 6. Mean run speeds 24.5, 29.8
and 23.3 um/s. Mean tumble speeds 12.1, 14.0 and 10.3 um/s. The paper states:

> "the speeds in both run and tumble phases and the mean tumble time show no
> systematic dependence on N."

This is the saturated regime. It agrees with Lisevich et al. above five.
Najafi J, Shaebani MR, John T, Altegoer F, Bange G, Wagner C. Flagellar number
governs bacterial spreading and transport efficiency. Sci Adv 2018;4:eaar6425.
DOI 10.1126/sciadv.aar6425. PMID 30263953.

**Darnton et al. 2007**, *E. coli*, high-speed imaging, 50 to 100 cells. The
abstract states:

> "a bundle of several flagella produced little more torque than a single
> flagellum produced."

This is the origin of the "thrust and drag scale together" claim. The paper
does not vary filament number systematically and reports no speed-versus-number
curve. It also reports 3.4 filaments per cell for the same strain.
Darnton NC, Turner L, Rojevsky S, Berg HC. On torque and tumbling in swimming
Escherichia coli. J Bacteriol 2007;189:1756-1764. DOI 10.1128/JB.01501-06.
PMID 17189361.

**Kamdar et al. 2023**, *E. coli*, high-throughput tracking plus transmission
electron microscopy on more than 60 bacteria. Flagella number rises linearly
with body length, and mean swimming speed is independent of body length. The
supplementary movie captions approximate the measured relation as N = L + 2,
with L in um. The explanation is load sharing: more flagella lower the load per
motor, the motors turn faster, and the extra body drag is cancelled. Note the
design: N and body length co-vary, so the study does not isolate N.
Kamdar S, Ghosh D, Lee W, Tătulea-Codrean M, Kim Y, Ghosh S, Kim Y, Cheepuru T,
Lauga E, Lim S, Cheng X. Multiflagellarity leads to the size-independent
swimming speed of peritrichous bacteria. Proc Natl Acad Sci USA
2023;120:e2310952120. DOI 10.1073/pnas.2310952120. PMID 37991946.

### Theory and simulation

**Nguyen and Graham 2018**, coarse-grained elastic model. Abstract:
"Swimming speed is also examined: it increases very weakly with number of
flagella and a simple theory is developed that explains this observation."
Nguyen FTM, Graham MD. Impacts of multiflagellarity on stability and speed of
bacterial locomotion. Phys Rev E 2018;98:042419.
DOI 10.1103/PhysRevE.98.042419.

**Kanehl and Ishikawa 2014**, boundary-element simulation. Propulsive
efficiency rises with flagella number; energetic efficiency falls.
Kanehl P, Ishikawa T. Fluid mechanics of swimming bacteria with multiple
flagella. Phys Rev E 2014;89:042704. DOI 10.1103/PhysRevE.89.042704.
PMID 24827275.

**Tătulea-Codrean and Lauga 2024**, slender-body theory with the real
torque-speed curve of the motor. At constant motor torque, speed grows
monotonically with N. With the measured torque-speed curve, speed plateaus and
then falls above a critical number, "around four flagella" for *E. coli* in
water at 23 °C. The critical number rises with viscosity. This gives a physical
reason for the saturation that Lisevich et al. measured.
Tătulea-Codrean M, Lauga E. Physical mechanism reveals bacterial slowdown above
a critical number of flagella. J R Soc Interface 2024;21:20240283.
DOI 10.1098/rsif.2024.0283. PMID 39503268.

### Is a 2.1-fold flagella difference consistent with a 1.6-fold speed
### difference?

Qualitatively yes, quantitatively unconstrained. Our range lies inside the
rising regime that Lisevich et al. report, so a speed increase is expected.
No source gives a slope, so nothing fixes how large the increase should be.

If I force a power law on our three strain means, the exponent is not constant
(derived here):

| pair | N ratio | speed ratio | implied alpha |
|---|---|---|---|
| PproA to PproB | 2.12 | 1.61 | 0.63 |
| PproA to WT | 1.28 | 1.39 | 1.33 |
| WT to PproB | 1.66 | 1.16 | 0.29 |

A single power law does not describe our three strains. The pattern instead
matches saturation: the step from PproA to WT is steep, the step from WT to
PproB is shallow, and PproB sits near the plateau at four to five flagella.
That shape agrees with Lisevich et al. 2025 and with Tătulea-Codrean and
Lauga 2024.

**Verdict: insufficient evidence to make run speed an explicit function of
flagella number.** The literature gives the shape (rise, then plateau near
four to five) but no calibrated slope. Keep run speed as a measured input.

---

## 2. Tumble and reorientation frequency versus flagella number

**Answer: yes. Tumble frequency rises with flagella number, and one paper gives
an explicit formula.**

**Mears et al. 2014**, *E. coli*, optical trap plus fluorescent filament
imaging. 54 wild-type cells and 24 CheY* cells; 203 wild-type tumbles. This is
the key quantitative result. Under the veto model, tumble bias TB relates to
the clockwise bias CB of a single motor by

    TB = 1 - (1 - CB)^N

Wild-type cells tumble less than this predicts. The data collapse when N is
replaced by an effective number:

    N_eff = 1.27 × N_flag^0.5

The cause is correlation between motors on the same cell, driven by CheY-P
fluctuations. A control strain with constitutively active CheY, decoupled from
the chemotaxis network, follows the plain veto model with N_eff = N.
Critically for our model:

> "the number of flagella per cell did not have a significant effect on the
> switching rates between CCW and CW states"

So the per-motor switching rate is a constant. Only the number of motors that
can veto a run changes.
Mears PJ, Koirala S, Rao CV, Golding I, Chemla YR. Escherichia coli swimming is
robust against variations in flagellar number. eLife 2014;3:e01916.
DOI 10.7554/eLife.01916. PMID 24520165.

**Najafi et al. 2018**, *B. subtilis*. Mean run time falls from 4.39 s
(N = 9) to 2.27 s (N = 26) to 1.18 s (N = 41). Mean tumble time stays at 0.24,
0.22 and 0.24 s. More flagella therefore raise the run-to-tumble rate and leave
the tumble duration unchanged.
Converting run times to rates and fitting an exponent (derived here) gives
`rate ~ N^0.62` between N = 9 and 26, and `rate ~ N^0.87` between N = 9 and 41.
The Mears exponent of 0.5 is close but on the low side. The truth for
*B. subtilis* lies between `sqrt(N)` and `N`.
DOI 10.1126/sciadv.aar6425. PMID 30263953.

**Terasawa et al. 2011**, *E. coli*, bead assay on two motors of the same cell.
Motor reversals on one cell are coordinated, with a subsecond delay that tracks
the distance from the chemoreceptor patch. Coordination is lost in a
constitutively active CheY mutant. This is the mechanism behind N_eff < N.
Terasawa S, Fukuoka H, Inoue Y, Sagawa T, Takahashi H, Ishijima A. Coordinated
reversal of flagellar motors on a single Escherichia coli cell. Biophys J
2011;100:2193-2200. DOI 10.1016/j.bpj.2011.03.030. PMID 21539787.

**Verdict: yes. The literature supports an explicit reorientation rate
proportional to N_eff = 1.27 × N^0.5.** This is the single best-supported
relation in the whole survey.

---

## 3. Turn angle versus flagella number

**Answer: yes, but the controlling quantity is the number of filaments that
leave the bundle, not the total number on the cell.**

**Turner, Ryu and Berg 2000**, *E. coli*, fluorescent filaments, 167 tumble
events. Filaments per cell 3.37 ± 1.59 for the main dye. Mean change in
direction:

> "The change in direction from run to run for the events of Table 1 was
> 58 ± 40°."

On the dependence:

> "Large changes in direction tended to occur when all of the filaments were
> involved in the tumble. When smaller numbers were involved, the distributions
> peaked more in the forward direction, and many of the events were below the
> threshold used to identify tumbles in the tracking experiments (35°)."

Caveat: the dependence appears as scatter and polar plots and is stated
qualitatively. The paper gives no per-bin mean turn angle, no correlation
coefficient and no statistical test. The independent variable is the *fraction*
of filaments that leave the bundle, within cells of fixed filament number
(two to five).
Turner L, Ryu WS, Berg HC. Real-time imaging of fluorescent flagellar
filaments. J Bacteriol 2000;182:2793-2801.
DOI 10.1128/JB.182.10.2793-2801.2000. PMID 10781548.

**Najafi et al. 2018**, *B. subtilis*. The turn-angle persistence
p_T = ⟨cos phi⟩ between successive runs falls with flagella number: 0.65
(N = 9), 0.59 (N = 26), 0.43 (N = 41). Falling p_T means larger mean turns.
The paper states that the mean of P(phi) shifts "toward larger angles with
increasing N". The mean absolute turn angles in degrees appear only in their
Figure 2G; those values are **not verified**.
DOI 10.1126/sciadv.aar6425. PMID 30263953.

**Dvoriashyna and Lauga 2021**, hydrodynamic model of a tumble in *E. coli*.
Mean reorientation angle against the number of filaments out of the bundle
N_u: 47.2 ± 21.2° (N_u = 1), 52.2 ± 30.3° (2), 56.7 ± 33.4° (3),
60 ± 34.6° (4). This is the only quantitative turn-angle-versus-number curve I
found, and it is a simulation, not a measurement. The paper also notes that
the experiments it compares to "could not distinguish between different number
of flagella". It reports the measured mean turn angle as "about 62°-68°, as
first measured by Berg and Brown (1972)".
Dvoriashyna M, Lauga E. Hydrodynamics and direction change of tumbling
bacteria. PLoS One 2021;16:e0254551. DOI 10.1371/journal.pone.0254551.
PMID 34283850.

**Vladimirov, Lebiedz and Sourjik 2010**, *E. coli* simulation, 1000 cells per
condition. They implement the Turner et al. relation: the turn angle rises with
the number of motors that switch clockwise. Effect on chemotaxis: a 3°
difference in mean tumble angle raises the population drift velocity by 52%,
from 0.92 to 1.4 um/s. Report this as "up to about twofold", not as "doubles";
the twofold figure applies to the simplified control and the steepest gradient.
Vladimirov N, Lebiedz D, Sourjik V. Predicted auxiliary navigation mechanism of
peritrichously flagellated chemotactic bacteria. PLoS Comput Biol
2010;6:e1000717. DOI 10.1371/journal.pcbi.1000717. PMID 20333235.

**Berg and Brown 1972**, *E. coli*, three-dimensional tracking. The classic
turn-angle distribution. I could not read the full text; it is paywalled and
absent from PubMed Central. Any number attributed to it here comes from
secondary reports, and is flagged as such. Flagella number is not a variable in
that study.
Berg HC, Brown DA. Chemotaxis in Escherichia coli analysed by
three-dimensional tracking. Nature 1972;239:500-504. DOI 10.1038/239500a0.
PMID 4563019.

**Nakai, Ando and Goto 2021**, *Salmonella* Typhimurium SJW1103, 23 cells
tracked for more than 30 s each, 268 tumbles in the best cell. This is the only
*Salmonella* run-and-tumble study with turn-angle statistics that I found. Turn
angle depends on the chemotactic state, not on flagella number: cells swimming
up a serine gradient turn by smaller angles, cells swimming down turn almost
uniformly. The paper attributes this to fewer filaments leaving the bundle.
Nakai T, Ando T, Goto T. Biased reorientation in the chemotaxis of peritrichous
bacteria Salmonella enterica serovar Typhimurium. Biophys J
2021;120:2623-2630. DOI 10.1016/j.bpj.2021.04.033. PMID 33964275.

**Kong et al. 2015**, bead-spring simulation. Abstract: "variation in tumbling
angle arises from variation in flagellar number and location on the bacterial
body". Simulation only.
The abstract adds that the tumbling angle rises "roughly linearly" with the
duration of the tumble, up to about 40 to 50 degrees, and more weakly above.
Kong M, Wu Y, Li G, Larson RG. A bead-spring model for running and tumbling of
flagellated swimmers: detailed predictions compared to experimental data for
E. coli. Soft Matter 2015;11:1572-1581. DOI 10.1039/c4sm02437k. PMID 25591165.

**Verdict: partial.** Turn angle grows with the number of filaments that leave
the bundle. The only quantitative curve is a simulation. For total flagella
number, the only measurement is *B. subtilis* at N = 9 to 41, far above our
range. Not strong enough to drive a per-strain parameter.

---

## 4. Rotational diffusion and directional persistence during runs

**Answer: essentially no primary answer. The one measurement runs in the
unexpected direction.**

**Najafi et al. 2018**, *B. subtilis*. The run-phase directional persistency
p_R falls with flagella number: 0.99 (N = 9), 0.98 (N = 26), 0.95 (N = 41).
The paper states: "the run paths are less curved for smaller N". So a larger
bundle makes runs LESS straight, not more. The authors attribute this to
multiple bundles forming at high N, which cannot happen at N = 2 to 4.
They also report an asymptotic rotational-diffusion coefficient D_R per strain
in their Figure 1D; the numeric values are in the figure only and are
**not verified**.
In their parameter sweep, p_R dominates transport: varying p_R over the
accessible range changes the asymptotic diffusion coefficient by a factor of
3.6, against 1.8 and 1.3 for the two other parameters.
DOI 10.1126/sciadv.aar6425. PMID 30263953.

**Nguyen and Graham 2018**, simulation. Adding a second flagellum "greatly
expands the parameter regime of stable locomotion". That is stability against
hook buckling, not directional persistence during a run. It does not support
the idea that a larger bundle holds the heading straighter.
DOI 10.1103/PhysRevE.98.042419.

**Saragosti, Silberzan and Buguin 2012**, *E. coli*. Measured rotational
diffusion coefficients: D_r = 3.5 ± 0.3 rad^2 s^-1 fitted to the Berg and Brown
reorientation distribution, and D_r = 2.1 ± 0.3 rad^2 s^-1 from their own data;
2.4 rad^2 s^-1 in LB and 1.6 rad^2 s^-1 in M9. They quote 0.16 rad^2 s^-1 as
the thermal value for a 1 um sphere. Important: these describe reorientation
during tumbles, modelled as active rotational diffusion. They are not run-phase
Brownian rotation, and flagella number is not a variable. The abstract does
close with a hypothesis worth noting: in steep gradients the effective
rotational diffusion coefficient itself varies with the direction of the
preceding run, and the authors "propose that this effect is related to the
number of flagella involved in the reorientation process". That is a proposal,
not a measurement.
Saragosti J, Silberzan P, Buguin A. Modeling E. coli tumbles by rotational
diffusion. Implications for chemotaxis. PLoS One 2012;7:e35412.
DOI 10.1371/journal.pone.0035412. PMID 22530021.

**Verdict: insufficient evidence.** For *E. coli* and *Salmonella* there is no
measurement of run-phase rotational diffusion as a function of flagella number.
The single *B. subtilis* datum has the opposite sign to the physical intuition
and comes from cells with 9 to 41 flagella.

---

## 5. Motile fraction versus flagella number

**Answer: yes. This is the second best-supported relation, and it has a clean
regime boundary at about four flagella per cell.**

**Honda et al. 2022**, *E. coli* K-12, filaments stained with FliC S219C plus
Alexa Fluor maleimide, 60 to 100 cells imaged per experiment, hundreds of cells
tracked. A cell counts as non-motile below 5 um/s. The key statements:

> "The observed four or five flagella per cell is the minimum number needed to
> keep the majority of cells motile."

> "When the expression of motility genes is low, such that there are on average
> less than four flagella per cell, the motile fraction is proportional to the
> average flagella number."

> "The average number of filaments varied strongly for the titratable flhDC
> strain as the provided inducer concentration was varied. Particularly, the
> fraction of cells with zero or one filament clearly increased at lower
> inducer concentrations."

> "The fraction of swimming cells (αm) remained close to 90% for all growth
> conditions."

So the motile fraction is set by the zero-and-one-filament tail of the per-cell
distribution, and it saturates once the mean passes about four.
Honda T, Cremer J, Mancini L, Zhang Z, Pilizota T, Hwa T. Coordination of gene
expression with cell size enables Escherichia coli to efficiently maintain
motility across conditions. Proc Natl Acad Sci USA 2022;119:e2110342119.
DOI 10.1073/pnas.2110342119. PMID 36067284.

**Lisevich et al. 2025** corroborates. They report that the fraction of
well-swimming cells and the swimming velocity of those cells follow the same
pattern against flagellar gene expression. They also describe a bimodal regime:

> "the bimodality, which occurs when the expression falls below the level at
> which two flagella per cell are synthesized and flagellar length decreases,
> serves to avoid the emergence of 'average', poorly motile phenotypes with a
> single and shorter flagellum"

DOI 10.1038/s41467-025-56980-x. PMID 39966405.

**Flagella-number distributions.** *B. subtilis* basal-body counts:
26 ± 6 (wild type, N = 42 cells), 9 ± 2 (ΔswrA, N = 43), 41 ± 6 (SwrA
overexpression, N = 42). The same paper argues that peritrichous placement is
non-random, and that counts rise with cell length.
Guttenplan SB, Shaw S, Kearns DB. The cell biology of peritrichous flagella in
Bacillus subtilis. Mol Microbiol 2013;87:211-229. DOI 10.1111/mmi.12103.
PMID 23190039.

**Do not write "Poisson".** I found no primary source stating that the per-cell
flagella number is Poisson distributed. Guttenplan et al. argue against random
placement. No source gives an explicit percentage of zero-flagella cells.

**Fit to our data (derived here).** Our motile-fraction proxy is the fraction
of cells with at least one hook: 0.771, 0.889, 0.877 at mean hook numbers 2.09,
2.67 and 4.43. Strict proportionality to the mean fails, as the ratios
fraction/mean are 0.369, 0.333 and 0.198. But Honda's regime boundary explains
the shape: PproA and WT sit below four hooks per cell and differ strongly,
PproB sits above four and has saturated. Our PproB even falls slightly below
WT, which is consistent with a plateau plus measurement scatter.

**Verdict: yes, with a caveat.** The literature supports the idea that the
motile fraction follows the fraction of cells carrying at least one filament,
and that it saturates above about four per cell. In our model the motile
fraction is already a measured input, so no change is needed. The literature
supplies the mechanism, not a new parameter.

---

## 6. Flagella number in porous media and soft agar

**Answer: no primary study measures flagella-number variants in bulk liquid and
in a mesh side by side. The nearest evidence argues that tumble frequency
matters LESS in a mesh, not more.**

**No direct measurement exists.** I found no study that takes peritrichous
strains differing in flagella number per cell and measures them in bulk liquid
and in a porous medium. I also found no study relating swim-plate halo diameter
to a measured per-cell flagella number in *E. coli* or *Salmonella*. Both are
open gaps. Our data therefore have no direct precedent, which is an argument
for publishing them, not against.

**The nearest study varies flagellar system, not number.**
**Grognot et al. 2023**, *Vibrio alginolyticus*, polar-only (P) against polar
plus lateral (PL). 24,248 and 22,101 motile trajectories from three biological
replicates each. Verified numbers:

> "We find that lateral flagella do not increase the speed during the swim
> phases: The P phenotype is swimming faster than the PL phenotype at all soft
> agar concentrations tested."

> "on average, lateral flagella decrease the chance of stalling by a factor
> 1.7 ± 0.2 (mean ± SD) in 0.25% agar."

> "the fraction of time spent stalling is 1.4 times higher for the P than the
> PL phenotype at 0.25% agar."

> "Above approximately 0.15% agar or 1.4% PVP K90 (3.6 cP), the PL phenotype
> outperforms the P phenotype with respect to chemotactic drift velocity."

Reading for us: the mesh advantage of extra flagella comes from LESS STALLING,
not from more speed. Do not cite this as evidence that "more flagella help in
porous media" in a general sense. The organism is a *Vibrio*, and the variable
is a second, mechanically different flagellar system.
Grognot M, Nam JW, Elson LE, Taute KM. Physiological adaptation in flagellar
architecture improves Vibrio alginolyticus chemotaxis in complex environments.
Proc Natl Acad Sci USA 2023;120:e2301873120. DOI 10.1073/pnas.2301873120.
PMID 37579142.

**In a mesh, geometry sets the run length.**
**Bhattacharjee and Datta 2019**, *E. coli* W3110 in 3D porous media, 500 to
1500 cells tracked per medium. Mean hop length falls from 3.24 um in the least
dense medium to 2.14 um in the densest. Verified statements:

> "This agreement confirms that hops are guided by the geometry of the pore
> space itself."

> "flagellar unbundling—which leads to tumbling in unconfined media—is not
> required for cell trapping; instead, these measurements show that confinement
> can suppress unbundling"

> "the flagella continue to rotate as a bundle for ≈16 s, much longer than the
> mean unconfined run duration of 2 s"

This is the important point for our model. In a mesh, the pore geometry, not
the tumble rate, sets the run length. A flagella-number-dependent reorientation
rate should therefore matter LESS in agarose than in liquid, not more. Our
larger PproA deficit in agarose is not explained by a tumble-rate effect. The
stalling and escape terms are the likelier explanation, in line with Grognot
et al. above.
Bhattacharjee T, Datta SS. Bacterial hopping and trapping in porous media. Nat
Commun 2019;10:2075. DOI 10.1038/s41467-019-10115-1. PMID 31061418.

**Supporting simulation.** An optimum appears when the run length matches the
longest straight path in the pore space.
Kurzthaler C, Mandal S, Bhattacharjee T, Löwen H, Datta SS, Stone HA. A
geometric criterion for the optimal spreading of active polymers in porous
media. Nat Commun 2021;12:7088. DOI 10.1038/s41467-021-26942-0. PMID 34873164.

**Gel concentration, not flagella number.** Front speed in soft agar against
agar concentration, 0.15 to 0.5 % w/v.
Croze OA, Ferguson GP, Cates ME, Poon WCK. Migration of chemotactic bacteria in
soft agar: role of gel concentration. Biophys J 2011;101:525-534.
DOI 10.1016/j.bpj.2011.06.023. PMID 21806920.

**Viscosity prediction.** Tătulea-Codrean and Lauga 2024 predict that the
critical flagella number rises with viscosity, so more flagella pay off in
thicker media. This is a simulation result, not a measurement in a mesh.
DOI 10.1098/rsif.2024.0283. PMID 39503268.

**Verdict: insufficient evidence.** No primary measurement links flagella
number to performance in a mesh for a peritrichous organism. The available
mechanism, less stalling, points at our stall parameters, not at our turning
parameters.

---

## Summary table

| # | question | best evidence | organism | supports tying the parameter to N? |
|---|---|---|---|---|
| 1 | speed vs N | Lisevich 2025; Najafi 2018 | *E. coli*; *B. subtilis* | **no** — shape known, slope not |
| 2 | tumble rate vs N | Mears 2014; Najafi 2018 | *E. coli*; *B. subtilis* | **yes** |
| 3 | turn angle vs N | Turner 2000; Najafi 2018; Dvoriashyna 2021 | *E. coli*; *B. subtilis* | **partial** — depends on filaments leaving the bundle |
| 4 | run persistence vs N | Najafi 2018 only | *B. subtilis* | **no** |
| 5 | motile fraction vs N | Honda 2022; Lisevich 2025 | *E. coli* | **yes**, but it is already a measured input |
| 6 | porous media vs N | none direct | — | **no** |

---

## Recommendation

**Make one parameter an explicit function of flagella number: the reorientation
rate.**

The literature supports exactly one calibrated relation. Mears et al. 2014
measured, in *E. coli*, that the per-motor clockwise switching rate does not
depend on flagella number, and that the cell behaves as if it carried

    N_eff = 1.27 × N^0.5

independent motors. Under the veto rule, a run ends when any one of these
motors turns clockwise. The run-to-tumble rate is therefore

    lambda(N) = k · 1.27 · sqrt(N)

with a single per-motor rate constant `k` fitted once across all strains,
instead of one directional-persistence term fitted per strain. This is the
change the revision needs: three fitted numbers become one.

Predicted effect for our strains (derived here): sqrt(N) equals 1.446, 1.634
and 2.105 for PproA, WT and PproB. The reorientation rate of PproB should
therefore be about 46 % higher than that of PproA. That is a modest, testable
prediction.

**Honest limits of the form, state them in the manuscript.**

1. The exponent 0.5 comes from *E. coli* at N = 1 to about 5 — the right
   organism family and the right range, but not *Salmonella*.
2. The *B. subtilis* run times imply an exponent between 0.62 and 0.87
   (derived here from Najafi et al. 2018). So 0.5 is a lower bound. If a
   sensitivity test is wanted, run `sqrt(N)` and `N` as the two brackets.
3. The relation predicts a rate, and our model uses a rate plus a
   heading-diffusion term. Only the reorientation rate should carry the N
   dependence. The heading-diffusion coefficient has no literature support for
   an N dependence, and the one measurement that exists has the wrong sign.

**Do not tie these to flagella number.**

- **Run speed.** Keep it as a measured per-strain input. The literature gives
  the shape but no slope, and our own three strains do not follow a single
  power law.
- **Motile fraction.** Keep it as a measured per-strain input. Honda et al.
  2022 explains why it behaves as it does; it does not supply a better model.
- **Heading diffusion.** No support. See question 4.
- **Turn angle spread.** The dependence is on the number of filaments that
  leave the bundle, which our model does not resolve. The only quantitative
  curve is a simulation (Dvoriashyna and Lauga 2021: 47.2°, 52.2°, 56.7°, 60°
  for one to four filaments out). If a second N-dependent parameter is ever
  wanted, this is the next candidate, but it needs the sub-model that tracks
  how many motors reversed.
- **Stall probability and stall duration.** No flagella-number measurement
  exists. Note, though, that the porous-media literature points here, not at
  turning, as the place where flagella number could act in agarose (Grognot et
  al. 2023: lateral flagella cut the chance of stalling by 1.7 ± 0.2 in 0.25 %
  agar). This is the honest home for our agarose result, and a clean open
  question to state in the discussion.
