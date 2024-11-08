# Changelog

## [0.4.2](https://github.com/oplik0/mn2/compare/v0.4.1...v0.4.2) (2024-11-08)


### Bug Fixes

* don't minify in action ([fd8b0f3](https://github.com/oplik0/mn2/commit/fd8b0f3d8bcaa4715658b1181d5b19d7f5bb5094))

## [0.4.1](https://github.com/oplik0/mn2/compare/v0.4.0...v0.4.1) (2024-11-08)


### Bug Fixes

* **deps:** update dependency prompt-toolkit to v3.0.48 ([#19](https://github.com/oplik0/mn2/issues/19)) ([6f9ed52](https://github.com/oplik0/mn2/commit/6f9ed52f20b97e7c51469c3ea3617bbe65061ffb))

## [0.4.0](https://github.com/oplik0/mn2/compare/v0.3.1...v0.4.0) (2023-10-28)


### Features

* send individual commands to different hosts ([1eb6488](https://github.com/oplik0/mn2/commit/1eb64883c42219a402c84503d64a99e823833410))


### Bug Fixes

* far more reliable udp iperf output ([b0dde0f](https://github.com/oplik0/mn2/commit/b0dde0fc805dade821a2ee333029560e5cd3b585))
* only add length to server if dualtest or tradeoff are active ([52eabef](https://github.com/oplik0/mn2/commit/52eabefba11b88b9e0e3f7f59dfba35e53df573c))
* remove some debugging remnants ([fadabf2](https://github.com/oplik0/mn2/commit/fadabf27a4a6b29038ca644b435be631980b07d4))
* use separate ports for UDP ([583911c](https://github.com/oplik0/mn2/commit/583911c4803c9221e639d59d918b5e7d8fb806a3))

## [0.3.1](https://github.com/oplik0/mn2/compare/v0.3.0...v0.3.1) (2023-10-27)


### Bug Fixes

* format m/g mixup ([6677155](https://github.com/oplik0/mn2/commit/667715530220cedcf55de7c63568a99bc3fe1e43))

## [0.3.0](https://github.com/oplik0/mn2/compare/v0.2.2...v0.3.0) (2023-10-27)


### Features

* output redirection ([b44b4f5](https://github.com/oplik0/mn2/commit/b44b4f547ae133aaa6f29571cd74b2566b973765))
* parallel iperf ([3982669](https://github.com/oplik0/mn2/commit/398266913dfba806118125fa663cfc7bdad65260))
* pass non-keyword args as just args to source ([9702668](https://github.com/oplik0/mn2/commit/97026683b73260528fc7d6eca5f359535c66b194))


### Bug Fixes

* add iperf timeout and client-server swap on udp ([b9912b6](https://github.com/oplik0/mn2/commit/b9912b63eadd20e7875f3ad1200765d5d985f12a))
* better error handling in source ([3f15d7d](https://github.com/oplik0/mn2/commit/3f15d7dcbea23e56abbd2328a410f5d4dcaae490))

## [0.2.2](https://github.com/oplik0/mn2/compare/v0.2.1...v0.2.2) (2023-10-23)


### Bug Fixes

* startup issue ([9c002ea](https://github.com/oplik0/mn2/commit/9c002ea14078ef2a25de0bae624318bcb4b641a5))

## [0.2.1](https://github.com/oplik0/mn2/compare/v0.2.0...v0.2.1) (2023-10-23)


### Bug Fixes

* stickytape build issue ([fa1ea89](https://github.com/oplik0/mn2/commit/fa1ea8905630317292b7654f2512ab5185559b64))

## [0.2.0](https://github.com/oplik0/mn2/compare/v0.1.0...v0.2.0) (2023-10-23)


### Features

* cache dependencies, resovles [#10](https://github.com/oplik0/mn2/issues/10) ([33e38a5](https://github.com/oplik0/mn2/commit/33e38a50b75dd2ad0f78a0ab77383736147c40a9))
* run files without command ([78f03c8](https://github.com/oplik0/mn2/commit/78f03c8b934505cc3578901da508a7653877bea4))
* start organizing the project ([ce7c39c](https://github.com/oplik0/mn2/commit/ce7c39c93ef3c826951b75ccea7a3b6592c29f88))


### Documentation

* add direct download link ([250b0b1](https://github.com/oplik0/mn2/commit/250b0b16bb5687187a3e38e7d43336b2d4dd9daa))
* add sample screenshot ([25cc84d](https://github.com/oplik0/mn2/commit/25cc84db9aa5f1e2c8da37043336eea721391fa9))
* finish last sentence ([18f18de](https://github.com/oplik0/mn2/commit/18f18de23bec634aeea2f6bb27b786873980dc36))
* fix small typo ([2e59ab7](https://github.com/oplik0/mn2/commit/2e59ab7412b2e23e59a49ad06048864c638c8788))

## 0.1.0 (2023-10-22)


### Features

* autocomplete, suggestions, etc. ([0bfe43d](https://github.com/oplik0/mn2/commit/0bfe43d973767f2f8b5a3e246801150f36400a2c))
* basic replacement with no new features yet ([5595720](https://github.com/oplik0/mn2/commit/5595720c5563a90de054f11c297a9a3782a3bf02))
* better UDP iperf reporting ([d9076ca](https://github.com/oplik0/mn2/commit/d9076ca43633a3ea8e925d9ab7f6311bf96df1eb))
* minify production build ([ba849cd](https://github.com/oplik0/mn2/commit/ba849cd4830fe640c9c842aef848d3ac327bad64))
* move to prompt_toolkit and typer ([d5cea1a](https://github.com/oplik0/mn2/commit/d5cea1a92384928e8476e52f6ad4204be82c80d0))
* option completion ([ecf073c](https://github.com/oplik0/mn2/commit/ecf073c8007c96df26f7f47b7f42ae3fa8ca80a1))
* option completions ([1aa8482](https://github.com/oplik0/mn2/commit/1aa848261f3fb52ab48fd84038df129fa6a28fd4))
* rest of mininet CLI ([3d2f29e](https://github.com/oplik0/mn2/commit/3d2f29e6b748e11fac89d7015e8fd6b934f6ca01))
* variables in source command ([d56ebe9](https://github.com/oplik0/mn2/commit/d56ebe98a5eaa057ba737ae860cccfad5a19aa21))


### Bug Fixes

* exit command ([5f0421e](https://github.com/oplik0/mn2/commit/5f0421e1ca6ed85c8ad5f7321f71ebf9d3e38fa5))
* remove cmd2 from dependencies ([5bc9665](https://github.com/oplik0/mn2/commit/5bc96653f58aeefc44be8b2147a778f137f26dde))
* remove option autocomplete since it doesn't work ([e60e4ff](https://github.com/oplik0/mn2/commit/e60e4ff4407603c871cd69df5372e25794436330))


### Documentation

* add a README ([ecfc3bd](https://github.com/oplik0/mn2/commit/ecfc3bd77c26e7f65e810c056cc5cd43d3108aa6))
