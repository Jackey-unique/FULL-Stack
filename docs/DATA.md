# Data provenance and preparation

The student's plan names these mirrors:
- https://huggingface.co/datasets/RichardErkhov/dhcp_dmri_pipeline
- https://huggingface.co/datasets/RichardErkhov/dhcp_fmri_pipeline

Direct online inspection timed out. The implementation instead inspected the already downloaded local directories supplied by the user. Their dataset_description.json files identify dHCP neonatal derivatives and the dHCP Consortium. The descriptions and source paths are retained in data/private/. No claim is made that this project independently verified the mirror's chain of authorization.

## Real import

Read participants.tsv keyed by pseudonymous participant_id. Read each sub-*/sub-*_sessions.tsv. Join dMRI/fMRI records by (participant, session); do not join on participant alone because repeat scans exist. Map scan_age to age_at_scan_weeks and birth_age to birth_age_weeks. Preserve original TSV fields under source_metadata. Keep ages numeric and missing/unparseable values null. Store sex, source, status, modality booleans, nested file records, notes and analyses.

Check the session directory for the expected primary preprocessed dMRI/BOLD image. Presence requires size >1024 bytes and gzip magic bytes. This filters empty files and obvious LFS pointer files but does not validate the entire compressed stream or NIfTI content. Metadata-only sessions remain in the collection with unavailable image flags. Never generate missing images, ages or predictions.

The initial import found 558 session records; 546 had metadata in both modality trees; 490 had detectable dMRI primary images, 512 had fMRI primary images and 444 had both. 12,514 local files were indexed. Numbers are a snapshot and can change as downloads complete. Run the importer with --refresh-files to update file availability without overwriting user data.

One session had an inconsistent birth age greater than scan age in both source trees. The normalized birth age was set to null, the raw value retained, and two source-specific observations recorded in data/private/import_report.json. This is a data-quality flag, not a clinical conclusion.

Each real sample starts with an importer-generated note explicitly describing its provenance/file status. These are software import observations, not invented clinical observations. No analyses or brain-age estimates are added to real records by the importer.

## Storage and distribution

Large MRI files remain in the original desktop dataset directories. MongoDB stores only metadata and relative file references; data/private/source_paths.json records the local roots. All project code and generated data are inside the requested full stack folder. Keeping originals in place avoids duplicating hundreds of image files or interrupting downloads.

The bundled dHCPUserTerms.pdf includes confidentiality/redistribution conditions. The application stays local, imports real records as private, and excludes local research metadata/images from the submission ZIPs. exports/local is a local database backup, not a public submission package. Before sharing any actual dHCP data, the user must determine that recipients and the proposed use meet the applicable terms. The project does not accept terms on the user's behalf or establish clinical/ethical approval.

The acknowledgment supplied with the data reads: These results were obtained using data made available from the Developing Human Connectome Project funded by the European Research Council under the European Union's Seventh Framework Programme (FP/2007-2013) / ERC Grant Agreement no. [319456]. Use appropriate original method references for any actual research results.

## Synthetic demonstration

scripts/seed_demo.py creates 150 wholly synthetic samples in brainage_demo using random seed 661. Invented age differences exercise API functionality and are marked synthetic_demonstration. Modalities in that database are fixture flags; they do not refer to actual images. They are suitable for showing CRUD and aggregation behavior, not validating a scientific model. Exports are generated from the running MongoDB with mongoexport, retaining ObjectIds and dates as Canonical Extended JSON.

## Precomputed results

No brain-age model weights or precomputed age prediction files were found in the supplied trees by filename inspection. The current application accepts authorized results via POST /samples/{id}/analyses or scripts/import_results.py. It requires method, model version and provenance and stores a derived signed age difference. A real inference pipeline would be a separate research extension requiring a selected validated model, compatible preprocessing and evaluation data.
