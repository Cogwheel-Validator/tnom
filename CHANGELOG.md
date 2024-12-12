# Change log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2024-12-11

### Added

- Added prometheus client
- Added new argument flags for prometheus

### Fixed

- Fixed the issue with task not shutting down gracefully

### Changed

- Small changes to dead man switch  to adjust to work with async tasks


## [0.4.2] - 2024-12-10

### Fixed

- Fixed the issue to send alert info alert when API comes back 

## [0.4.1] - 2024-12-09

### Fixed 

- Fixed the issue when there is working API, when the API was not working it would return NoneType which caused monitoring tool to fail to send alert if there wasn't working API

## [0.4.0] - 2024-12-05

### Added

- Alert if there is no working API to query from
- Added logic to check if the database schema is up to date and update it if needed

## [0.3.0] - 2024-12-01
First official public version of the monitoring tool

- Monitoring system for wallet balance and unsigned oracle events
- Pagerduty and Telegram alerts
- Dead man switch
- Manage and setup SQLite database on its own