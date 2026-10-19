## Purpose

Lets users fetch the project's command-line tools from an Apache web server through a simple HTML page that lists each tool with a working download link.

## ADDED Requirements

### Requirement: List each tool with a download link
The page SHALL show the available tools and, for each one, provide a link that downloads the corresponding script source from the served folder.

#### Scenario: Download a listed tool
- **WHEN** a user opens the page and clicks a tool's download link
- **THEN** the browser downloads the script for that tool from the server

#### Scenario: HTML page is served by Apache
- **WHEN** the download folder is served by Apache
- **THEN** a user can open the page in a browser and download the tools from that server

### Requirement: Reflect the current tools
The download folder SHALL contain the same tool scripts as the project root, so what users download matches the current versions of the tools.

#### Scenario: Download folder is in sync with the project
- **WHEN** the tool scripts are copied into the served folder
- **THEN** each download link retrieves the current version of that tool