# Changelog

All notable changes to this project will be documented in this file. This changelog tracks project-wide updates independently of any individual game modules.

## [Unreleased]
### Added
- Established a project-wide changelog to capture shared updates across games.

### Changed
- Relocated shared localization assets and deck utilities to a root-level `shared` directory for reuse across game modules.
- Enhanced the shared deck module to version 2 with multi-deck construction, discard recycling, card parsing helpers, and accompanying tests.
- Updated GUI localization loading paths and deck tests to align with the new shared resource location.
