# Publish this repository to GitHub

Destination: https://github.com/amin-kamaleddin/Physical-AI-in-Psychiatry

The archive unpacks to a complete repository **root**, containing `README.md`,
`run_all.py`, `outputs/`, `figures/`, and `.github/`. Push the unpacked contents,
not the ZIP file itself.

## Terminal push (macOS, Linux, Git Bash)

From the extracted `Physical_AI_Psychiatry_GitHub_Public_Release_v4.5` folder:

```bash
git init -b main
git remote add origin https://github.com/amin-kamaleddin/Physical-AI-in-Psychiatry.git
git add .
git commit -m "Release reproducible Physical AI in Psychiatry simulations v4.5"
git push -u origin main
```

This assumes that your destination GitHub repo is empty. If GitHub reports a
pre-existing main branch or `non-fast-forward`, inspect its contents and merge
first; **do not force-push**. Authentication requires a GitHub account with
write permission, via your Git credential manager, SSH, or `gh auth login`.

The connected GitHub integration consulted during preparation had read-only
access; it could not perform an upload without the repository owner's
authorization.

## Before describing this as open-source or journal-archived

1. Confirm publication rights for code, derived outputs, images and text.
2. Select and approve a genuine software license; replace `LICENSE_STATUS.md`
   with the approved `LICENSE` and update the README.
3. Fill `CITATION.cff.template` with genuine author metadata, rename it to
   `CITATION.cff`, and add the eventual archived DOI.
4. Update the manuscript's Data/Code Availability statements with the actual
   permanent archive DOI after a Zenodo/Figshare deposit or GitHub release.
5. Confirm the author-controlled journal statements in the pre-submission checklist.

Do not add patient data, clinical exports, tokens, proprietary model weights,
or credentials to this public repository.
