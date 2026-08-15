# Supplementary Figure 3

This analysis builds Supplementary Figure 3. It was named `supplementary_04` until 15 August 2026, because it built Supplementary Figure 4 before the 12 August 2026 renumbering. Directory and figure now agree.

Panels A-I map to legacy `Figure5A_motility-competition_agarose-liquid`. The columns compare WT/PproA, WT/PproB and PproA/PproB. The rows show median speed, swimming fraction and directional persistence. The legacy effective-diffusivity row was withdrawn on 12 August 2026. It read the same input file as Figure 7 and repeated Figure 7A-C with a different within-unit summary.

## What one panel shows

The panels follow Figure 7A-C. Inside a panel the two media stand side by side as two groups of paired violins, separated by a gap. Before 14 August 2026 both media shared one strain tick and the medium comparison was three lines of text in the panel corner.

One line joins the paired block-level values of one `metadata_key` in one medium. Each paired unit takes its own small horizontal offset, so every line starts and ends on its own marker.

Colour carries strain identity. The builder reads `get_strain_style` for the same three entries Figure 7A-C reads, so both figures take their colours from one place. Medium is carried by the group gap and by marker shape and fill: agarose is a filled circle, liquid an open square. The open marker keeps its border, because the border is the only edge of a white-faced mark.

A violin behind each group states the kernel density of the same unit values, on the plotted scale.

The black diamond is the group mean of the plotted quantity, the summary mark of Figures 4, 5 and 6. The second strain's diamond carries the paired 95 % interval, anchored at the first strain's mean. The plotted quantity is log10 on a ratio row and the raw value on the fraction row, so the anchored estimate lands on the second strain's own mean exactly; the builder asserts the residual is below 1e-12.

Each group prints its own header above the axes: the medium and its fill, the paired estimate, the 95 % interval and the unit count. The estimate is always the second strain against the first, in the order the x axis names them: a ratio on the speed and persistence rows, a difference on the swimming-fraction row. That wording is in the legend and in the `contrast` column of the effect table, not in the panel, which is how Figure 7A-C handles the same question. It cost 8 mm of panel height nine times over, and the figure stands 166 mm tall instead of 190 mm. The unit of analysis is the paired experimental unit, that is one `metadata_key` in one medium. The bootstrap resamples those units, never trajectories. It runs 10,000 iterations from seed 20260812, and the seed also takes the panel index, so one panel alone reproduces the numbers of a full run. No inferential test is displayed.

Median speed and directional persistence are drawn as log10 on a linear axis, and the ticks print the original unit. A log axis would estimate the violin density in the original unit and then stretch it. Swimming fraction is drawn on a linear axis.

The three panels of a metric row share one y range, so the three strain pairs are read on one scale. The cost is panel H, whose data occupy the upper half of the shared persistence axis.

Every panel places its axes in millimetres of the 55 x 48 mm assembly box, so all nine share one baseline. The plotted area keeps 29.6 mm of height, the row height of Figure 7A-C. The builder measures the rendered extent of every text it draws and fails the build if one of them reaches into the band the assembled panel letter covers.

## Counts and status

Paired experimental units per column, agarose and liquid: 18 and 16 for WT/PproA, 18 and 18 for WT/PproB, 18 and 16 for PproA/PproB. Every metric of a column reads the same paired set, and the builder asserts these counts.

The migrated 208-row processed table keeps metadata keys and derived values, but not raw trajectories. Biological and technical replicate definitions and upstream exclusions therefore stay legacy-derived, and every panel is a partial reproduction.

Source-data CSVs go to `data/source_data/supplementary_03/`: the plotted points and the annotated effects, one pair of files per panel. The effect table is also written to `build/statistics/Supplementary_Figure_3/<panel>/` and registered as `partial_statistics`, so every number a panel prints is machine-readable where a reader of Figure 7 looks for it. Panel graphics go to `build/panels/Supplementary_Figure_3/<panel>/` as PNG, SVG and PDF. Checksum-bearing provenance goes beside each panel and to `metadata/provenance/supplementary_03/`. Final 9-panel assembly and visual acceptance remain separate.

`INPUT_MANIFEST.md` records the canonical and byte-identical legacy input checksum, byte size and row count.

Run all panels: `.venv/bin/python3.12 analyses/supplementary_03/build_s3.py --panel all`.
