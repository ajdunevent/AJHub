# AJHub

Signed Flatpak repository for AJ's apps, hosted on GitHub Pages and published with [FrogPak](https://github.com/FrogPak/engine).
The landing page, with every app and its install command, is https://ajdunevent.github.io/AJHub/.

## Using it

```
flatpak remote-add --user --if-not-exists ajhub https://ajdunevent.github.io/AJHub/index.flatpakrepo
flatpak install --user ajhub <app ID>
```

Or install one app directly from its `.flatpakref` file, for example
`https://ajdunevent.github.io/AJHub/net.dunevent.Ripples.flatpakref`.

## How it works

The Publish workflow runs FrogPak, which checks each app in `pond.yml` for a new release every hour. When something changed, it imports the latest release bundles into a fresh signed Flatpak repository, builds the landing page, and deploys both to Pages. Only the newest version of each app is kept.

Each app's release workflow also starts Publish with `gh workflow run publish.yml` once its release is out, so new versions appear within minutes. Keep the workflow's file name and its `workflow_dispatch` trigger for that to work.

Adding an app: add an entry to `pond.yml` with its app ID, repository and release file pattern; the [configuration reference](https://frogpak.org/docs/configuration.html#apps) has every setting. The app's releases must include `<AppName>-<arch>-latest.flatpak` files, which the shared release workflow produces.

## One-time setup

1. Settings > Pages > Source: GitHub Actions.
2. Create the signing key (no passphrase, used only by this workflow):

   ```
   gpg --batch --quick-generate-key --passphrase '' "Dunevent Flatpak Repository" rsa4096 sign never
   gpg --list-secret-keys --keyid-format long
   gpg --armor --export-secret-keys <FINGERPRINT>
   ```

3. Settings > Secrets and variables > Actions > New repository secret:
   `GPG_PRIVATE_KEY`, containing the full armored output of the last command.
4. Back up the private key somewhere safe. Replacing it later means every user
   must re-add the remote.
5. Actions > Publish > Run workflow.
