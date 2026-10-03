# Sound effects

Tagged folders: `pops/`, `boings/`, `steps/`, `voice/`, `ui/`, `ambient/`. Phase 6 adds
`sfx_manifest.json`, which records each file's tag, source, licence and credit.

- Drop new downloads or iPhone recordings into `_inbox/`. The pipeline renames them and files them
  into the right folder.
- Put raw voice takes in `voice/_raw/`. The voice script cleans and pitch-shifts them into `voice/`.
- Log every third-party sound in `../LICENCES.md`.
