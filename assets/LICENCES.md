# Asset and sound licences

Every third-party file used in an episode needs a row here. From Phase 7, `python cc.py qa`
fails an episode that uses an unlisted asset.

Rules (guide §3.4, §14.2, §21):

- **Prefer CC0** (Poly Haven, Kenney, CC0-filtered Freesound). No credit needed, but still log it.
- **CC-BY:** allowed, but the "Credit text" must go in the caption or video description.
- **Never use CC-BY-NC or CC-BY-ND.** You plan to earn from the channel.
- **Pixabay:** keep the download page URL. It helps dispute a wrong Content ID claim.
- **Your own recordings / synthesised sounds:** licence `own`. There's no rights risk, but log them so QA can see them.
- **Instagram/Edits library music** is licensed only inside Meta's apps. It's never stored here and never baked into the YouTube file (§14.4).

| File (repo path) | Source page URL | Author | Licence | Credit text (if CC-BY) | Added |
|---|---|---|---|---|---|
