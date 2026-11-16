# Protecting the Steady source repository and distributing binaries

Prepared 16 November 2026 for `kartikjbsky/Steady`.

## Recommended structure

1. **Private source repository:** make the existing source repository private and use it for development, issues that contain confidential information, tests, and GitHub Actions.
2. **Public downloads repository:** create a separate public repository (suggested name: `Steady-Downloads`) containing only release installers, checksums, user-facing README/release notes, `LICENSE`, `EULA.md`, and third-party notices/licence texts. Do not put Python source, tests, build scripts, private workflows, local databases, backups, or development history in it.
3. Build binaries in the private source repository. Publish the resulting binaries to the public downloads repository manually at first. Automating cross-repository publishing can be added later using a narrowly scoped GitHub token stored as an Actions secret.

A private repository's Releases are not a public download service. If the existing repository becomes private, anonymous users will not be able to use it as the public download location. A separate public downloads repository avoids exposing the source while retaining a public place to get installers.

## Important consequences of making the current repository private

GitHub's current documentation states that when a public repository is changed to private:

- Existing public forks remain public and are detached into a separate network; they are not made private.
- Existing local clones and copies previously downloaded by people cannot be recalled by changing visibility.
- Stars and watchers on the repository are erased.
- Some GitHub security features may have different availability on private repositories depending on plan.

The repository currently appears public on GitHub. The public repository page showed zero forks at the time this guide was prepared, but that does not reveal private/local clones or downloaded source archives. Treat previously exposed source as already disclosed; changing visibility prevents casual future access but cannot guarantee that nobody retained a copy.

Official GitHub documentation:
- https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility
- https://docs.github.com/en/pull-requests/reference/forks

## Change the existing repository to private

1. Sign in to the GitHub account that owns `kartikjbsky/Steady`.
2. Open https://github.com/kartikjbsky/Steady.
3. Select **Settings** → **General**.
4. Scroll to **Danger Zone** → **Change repository visibility**.
5. Select **Make private**.
6. Read GitHub's warning carefully, confirm the repository name, and confirm the change.
7. Open the repository in a private browser/incognito window while signed out. It should no longer be publicly viewable.

Do not delete the old repository merely to try to remove copies; deletion does not recall existing forks or local clones.

## Create the public binary-download repository

1. Create a new repository named `Steady-Downloads` (or another product/download name).
2. Set it to **Public**.
3. Do not initialise it with the Python source tree.
4. Add a concise user-facing README with links to the releases, supported platforms, installation instructions, checksum verification, and a support email.
5. Add `LICENSE`, `EULA.md`, `THIRD_PARTY_NOTICES.md`, and the exact third-party licence texts/notices required for the shipped dependencies.
6. Publish only compiled archives/installers and checksum files as release assets. GitHub's automatic source archives for this small downloads repository will then contain only the public download-repository files, not the private Steady source.
7. Test the release download link while signed out of GitHub.

Initially, upload releases manually from the private source project's `release/` directory. Later, configure the private GitHub Actions workflow to publish the build artefacts to `Steady-Downloads` using a fine-grained token scoped only to that repository and only to the permissions needed to create releases/upload assets. Store the token as a GitHub Actions secret; never commit it to source.

## Secure the private source repository

- Enable two-factor authentication or a passkey on the GitHub account; store recovery codes securely.
- Review **Settings → Collaborators and teams** and remove anyone who no longer needs access.
- Review **Settings → Actions → General** and restrict workflow permissions to read-only by default; grant write permissions only to the release job that needs them.
- Use protected branches or a ruleset for `main`: block force pushes and deletion, require status checks before merging, and require pull requests if a second reviewer is available. For a solo-maintained project, configure this so you do not accidentally lock yourself out of normal releases.
- Enable Dependabot alerts and security updates where available. Review the dependency list and update dependencies deliberately.
- Keep `.gitignore` excluding `.venv/`, `dist/`, `build/`, `release/` when appropriate, `*.sqlite*`, backups, CSV exports, `.env`, credentials, and signing keys. Only commit release artefacts to the public downloads repository.
- Review the complete Git history for passwords, API keys, personal data, database files and backups. If a credential was ever committed to a public repository, revoke/rotate it immediately; deleting it in a later commit is not enough.
- Keep at least two encrypted backups of the private source repository and release signing materials, in locations separate from the development PC.

## Legal documents and app acceptance

- Put the proprietary `LICENSE` and `EULA.md` at the root of the source repository and include them with every public binary release.
- Add an explicit first-run EULA screen to Steady: show the EULA text or a reliable local copy, require an unchecked **I Agree** action, provide **Decline / Exit**, and store the accepted EULA version and timestamp locally. Make the EULA accessible later from Settings → Legal.
- Do not rely solely on a LICENSE file hidden in an archive or a passive “using means acceptance” sentence. Have Indian counsel review the click-through wording and the final distribution process.
- Keep the current `THIRD_PARTY_NOTICES.md`, but expand it into a release-specific notice bundle containing exact versions and copies/links to required licences. The current file is a pointer list, not a complete compliance audit.
- In particular, verify the exact PySide6/Qt modules and their licence mode and meet all LGPL/GPL or commercial Qt obligations for the binaries you ship. PyInstaller's bootloader exception does not remove the obligations of Qt or other bundled components. Do not assume the proprietary EULA overrides third-party open-source rights.
- Before claiming exclusive ownership of every asset or code file, verify that no contributor, employer, contractor, client or third-party licence has rights in it. Keep a record of authorship, dates, design files, source snapshots and contributor permissions.

## What a proprietary licence does and does not do

A proprietary licence states what users may do and what requires permission. It does not technically stop copying or reverse engineering. PyInstaller packaging is not strong source-code protection. Keeping the source repository private, distributing only binaries, signing releases, and using an explicit EULA improves control, but no ordinary desktop distribution can guarantee that nobody will copy or inspect it.

## India copyright registration

The Indian Copyright Office says computer software/programmes can be registered and that source code and object code are required with the application. Review the current official process and obtain legal advice before submitting material. Do not upload your full proprietary source code to public places as part of the registration process.

Official resources:
- https://copyright.gov.in/frmFAQ.aspx
- https://copyright.gov.in/UserRegistration/BOLoginPage.aspx

## Before first proprietary public distribution

- [ ] Make the source repository private.
- [ ] Audit forks, old source archives, Git history and credentials.
- [ ] Create a public downloads-only repository.
- [ ] Add the proprietary `LICENSE` and `EULA.md` to the app package and downloads repository.
- [ ] Complete a release-specific third-party licence audit and include the required texts/notices.
- [ ] Add and test first-run EULA acceptance and a Settings → Legal page.
- [ ] Test personal-use installation and update flows.
- [ ] Set up a separate paid commercial agreement, invoice process and licence records before accepting business customers.
- [ ] Have an Indian software/IP lawyer review the documents and distribution flow.
