# Sams Volleyball Tracker

### Custom component to access data from sams ticker in Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
![Version](https://img.shields.io/github/v/release/kloemi/ha-sams-volleyball)
[![Downloads](https://img.shields.io/github/downloads/kloemi/ha-sams-volleyball/total)](https://tooomm.github.io/github-release-stats/?username=kloemi&repository=ha-sams-volleyball)

This integration provides real-time scores for volleyball teams that are provided by [sams](http://www.sams-server.de/) ticker -  mainly all german and luxembourgish volleyball teams.

The initial version of that integration provides an entity compatible to the great work of [ha-teamtracker](https://github.com/vasqued2/ha-teamtracker) and can be used with the [ha-teamtracker-card](https://github.com/vasqued2/ha-teamtracker-card) to display the game information in the Home Assistant dashboard.

## Installation

### HACS

1. Install [HACS](https://github.com/custom-components/hacs).
2. Install Integration.
3. Restart Home Assistant
4. Add Integration via [UI](https://my.home-assistant.io/redirect/integrations/) or click [HERE](https://my.home-assistant.io/redirect/config_flow_start/?domain=samsvolleyball)

### Manual installation

1. Copy all files from custom_components/webuntis/ to custom_components/samsvolleyball/ inside your config Home Assistant directory.
2. Restart Home Assistant
4. Add Integration via [UI](https://my.home-assistant.io/redirect/integrations/) or click [HERE](https://my.home-assistant.io/redirect/config_flow_start/?domain=samsvolleyball)

## Configuration via UI
### Configure association
![image](https://github.com/kloemi/ha-sams-volleyball/assets/114607732/336a25f9-ce62-4e99-89ae-88ec16a2752a)
Select the association of the team you like to track

### Configure league
![image](https://github.com/kloemi/ha-sams-volleyball/assets/114607732/2ce38b8d-e513-47d6-9f46-3b1d07f5fa8a)

### Select your favourite team
![image](https://github.com/kloemi/ha-sams-volleyball/assets/114607732/8c73ceb3-f608-43ae-8a9a-d0c6cef5f1db)


## Entities

The integration creates per team an entity in the format `sensor.NAME_entity`.

|Sensor  |Type|Description
|:-----------|:---|:------------
|`sensor.team_name`| team_tracker | data compatible to ha-teamtracker.
