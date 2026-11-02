#!/usr/bin/env bash
# Builds a signed Flatpak repository from the bundles in a directory.
# Usage: build-repo.sh BUNDLE_DIR OUTPUT_DIR BASE_URL
# Needs GNUPGHOME to hold the signing key.
set -euo pipefail

bundles=$1
repo=$2
base_url=${3%/}/
title=${REPO_TITLE:-AJHub}
comment=${REPO_COMMENT:-"AJ's Flatpak Repository"}
remote_name=${REMOTE_NAME:-ajhub}
runtime_repo=https://dl.flathub.org/repo/flathub.flatpakrepo

keyid=$(gpg --list-secret-keys --with-colons | awk -F: '/^fpr:/{print $10; exit}')
[[ -n "$keyid" ]] || { echo "No signing key in $GNUPGHOME" >&2; exit 1; }
pubkey=$(gpg --export "$keyid" | base64 -w0)

ostree init --mode=archive --repo="$repo"
shopt -s nullglob
files=("$bundles"/*.flatpak)
(( ${#files[@]} )) || { echo "No bundles in $bundles" >&2; exit 1; }
for bundle in "${files[@]}"; do
    flatpak build-import-bundle --gpg-sign="$keyid" --gpg-homedir="$GNUPGHOME" "$repo" "$bundle"
done
flatpak build-update-repo --gpg-sign="$keyid" --gpg-homedir="$GNUPGHOME" \
    --title="$title" --comment="$comment" --prune "$repo"

cat > "$repo/index.flatpakrepo" <<REPO
[Flatpak Repo]
Title=$title
Comment=$comment
Url=$base_url
Homepage=$base_url
GPGKey=$pubkey
REPO

# One .flatpakref per application; a ref file also pulls the runtime from Flathub.
ostree refs --repo="$repo" | awk -F/ '$1 == "app" {print $2 " " $4}' | sort -u |
while read -r id branch; do
    cat > "$repo/$id.flatpakref" <<REF
[Flatpak Ref]
Title=$id
Name=$id
Branch=$branch
Url=$base_url
SuggestRemoteName=$remote_name
IsRuntime=false
GPGKey=$pubkey
RuntimeRepo=$runtime_repo
REF
done
