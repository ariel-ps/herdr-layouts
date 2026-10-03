#!/bin/sh
set -eu
root=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
cargo build --release --locked --manifest-path "$root/Cargo.toml" --target-dir "$root/target"
mkdir -p "$root/libexec"
cp "$root/target/release/herdr-named-tab" "$root/libexec/.herdr-named-tab.$$"
mv "$root/libexec/.herdr-named-tab.$$" "$root/libexec/herdr-named-tab"
