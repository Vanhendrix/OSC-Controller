---
type: context
created: 2026-07-03
updated: 2026-07-03
status: active
deadline:
tags:
  - blender
  - addon
  - osc
  - product
---

# OSC-Controller — Contexte projet

> FolderNote créée 2026-07-03 pour combler un gap : le code existe depuis mai 2026 (voir README.md), addon vendu sur SuperHive (stratégie business → [[10_PROJECTS/blender-osc-addon/blender-osc-addon|blender-osc-addon]]), mais aucun FolderNote de suivi technique n'existait. Référencé comme addon architecture par [[10_PROJECTS/PointCloudViewer/PointCloudViewer|PointCloudViewer]] (lien cassé jusqu'ici).

## Description

Addon Blender : réception messages OSC (UDP, `python-osc` bundled) → mapping vers shape keys, bone rotations, propriétés génériques (data path). Right-click sur une propriété Blender → création mapping auto. Auto-key en option.

## État actuel (vérifié 2026-07-03)

- Range mapping (`min_in`/`max_in`/`min_out`/`max_out`) déjà présent par mapping (`properties/scene_props.py:47-52,100-105`), toujours appliqué, pas de toggle.
- Pas de système presets (aucune trace `preset` dans le code).
- Preset ARKit : bouton "Add 50 Face Shape Key Mappings" existe (README) mais pas formalisé comme vrai preset (pas de save/load nommé).
- Pas de notion de groupe de mappings.

## Backlog produit (ouvert 2026-07-03)

### Remap on/off (codé 2026-07-04, pending test live)
- [x] Toggle disable remap **global** (`Scene.osc_remap_enabled`) — tous mappings passthrough valeur brute
- [x] Toggle disable remap **local** (`remap_enabled` par mapping, override le global — global OFF force passthrough même si local ON)
- Implémentation : `core/mapping.py::map_value()` retourne `v` inchangé si non-remap ; `build_mapping_table_extended()` calcule le flag effectif (`global AND local`) à la construction de la table

### Presets système (codé 2026-07-04, pending test live)
- [x] Save preset : capture tous les mappings actuels (ou juste la sélection) sous un nom — `core/presets.py` (JSON, `bpy.utils.user_resource('SCRIPTS', .../presets/osc_controller/')`, survit aux réinstalls addon)
- [x] Load preset : additif, ajoute les mappings du preset aux mappings existants
- [x] Delete all mappings (`OSC_OT_ClearAllMappings`, indépendant des presets) + Delete preset (fichier)
- [x] Groupes de mappings : checkbox `selected` par mapping (header row) → "Save Selected" ne capture que la sélection
- [x] Preset **ARKit 52 blendshapes** : formalisé — bouton existant renommé, se sauvegarde via le flow générique (pas de code spécifique nécessaire)
- [x] Preset **Camera** : `OSC_OT_CreateCameraMappings` — picker caméra scène (`Scene.osc_camera_preset_target`) → génère 6 mappings génériques (pos xyz + rot xyz), réutilise le flow save/load standard
- [ ] Preset **Viewfinder** : reporté — dépend des sockets exposés côté [[10_PROJECTS/viewfinder/viewfinder|viewfinder]] (backlog "Auto-registration params côté add-on OSC", pas fait)
- [ ] Preset **PointCloudViewer** : reporté — dépend features couleur (voir [[10_PROJECTS/PointCloudViewer/PointCloudViewer|PointCloudViewer]] backlog)
- [ ] **À tester en Blender** : toggle remap global/local, save all/selected, clear all, load, delete preset, camera mappings, ARKit preset

## Liens

- Stratégie business/growth (SuperHive, marketing) : [[10_PROJECTS/blender-osc-addon/blender-osc-addon|blender-osc-addon]]
- Addon utilisant OSC-Controller comme référence architecture : [[10_PROJECTS/PointCloudViewer/PointCloudViewer|PointCloudViewer]]
- Addon cible pour presets futurs : [[10_PROJECTS/viewfinder/viewfinder|viewfinder]]
- Code : `10_PROJECTS/OSC-Controller/` (symlinké côté desktop, voir `blender-dev-repo`)

## Contenu du dossier

```dataview
LIST
FROM "10_PROJECTS/OSC-Controller"
WHERE file.name != this.file.name
SORT file.mtime DESC
```
