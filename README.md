# Landscape Generator

![landscape-thumb](https://github.com/user-attachments/assets/817d6169-c9c3-43ad-ba3b-acf7a3818088)

**Author:** The French Monkey (TFMSTYLE)  
**Version:** 1.0.0  

---

## Overview

The Landscape Generator creates procedural terrains using layered noise algorithms and customizable geological parameters.  
It allows artists and designers to generate realistic or stylized landscapes with control over shape, scale, erosion, and surface variation.  
The system produces geometry-based terrain meshes that can be further sculpted, displaced, or textured directly within Blender.  
Ideal for creating mountains, valleys, dunes, or abstract terrain forms with minimal manual modeling effort.

---

## Parameters

### Live Update
Automatically regenerates the terrain in real-time when parameters are changed.  
Recommended to disable for very high-resolution meshes to preserve performance.

---

### Terrain Type
Defines the base formation style used to shape the terrain surface.  
Available options include:
- **Mountains:** Rugged and tall terrain with sharp ridges.  
- **Hills:** Smooth rolling elevations with soft transitions.  
- **Dunes:** Wind-formed shapes with wavy slopes and linear ridges.  
- **Craters:** Depressed terrain with circular cavities.  
- **Plateaus:** Flat-topped formations with cliff-like edges.  
- **Abstract:** Non-natural procedural shapes for artistic use.

---

### Size
Specifies the overall width and depth of the generated terrain area.  
Adjust this to define the spatial footprint of the landscape.

---

### Resolution
Controls the number of subdivisions used in the terrain grid.  
Higher resolutions produce more detailed features but require more processing power.

---

### Height
Determines the maximum elevation of the terrain.  
Affects how tall or flat the landscape appears.

---

### Noise Type
Selects the noise algorithm that defines the elevation pattern.  
Options typically include:
- **Perlin Noise:** Smooth, natural variation ideal for general terrain.  
- **Simplex Noise:** Less directional, efficient version of Perlin noise.  
- **Voronoi:** Creates cell-like or rocky structures.  
- **Multifractal:** Layered fractal noise with high complexity.  
- **Ridged Multifractal:** Emphasizes sharp peaks and valleys.  
- **Hybrid Multifractal:** Balanced result combining smooth and rough details.

---

### Noise Scale
Adjusts the scale of the noise pattern.  
Larger values create broader terrain features, while smaller ones add finer details.

---

### Noise Seed
Randomizes the procedural noise pattern.  
Changing this generates a different terrain layout without altering other parameters.

---

### Octaves
Controls the number of noise layers combined to create complexity.  
Higher values produce richer detail but increase computation time.

---

### Persistence
Determines the amplitude decay of successive noise octaves.  
Lower values make higher-frequency noise less pronounced.

---

### Lacunarity
Adjusts the frequency ratio between noise octaves.  
Higher values create more chaotic terrain patterns.

---

## Erosion

### Apply Erosion
Enables a simulated erosion system that mimics natural geological weathering.  
Generates realistic valleys and drainage patterns.

---

### Erosion Strength
Defines the intensity of erosion applied to the terrain surface.  
Higher values result in deeper erosion cuts.

---

### Iterations
Number of erosion simulation passes.  
More iterations create smoother and more natural erosion paths.

---

### Sediment Amount
Controls how much displaced material is redeposited in low areas.  
Adjust to fine-tune balance between carving and filling.

---

### Water Flow
Influences erosion patterns by simulating flow direction and strength.  
Higher values exaggerate valley carving.

---

## Terrain Filters

### Apply Smooth
Applies a smoothing filter to soften sharp features.

---

### Apply Sharpen
Enhances ridges and accentuates shape contrast for a more dramatic look.

---

### Flatten Peaks
Reduces extreme elevation spikes to create plateau-like areas.

---

### Flatten Valleys
Fills in low regions to create a more balanced elevation map.

---

## Surface Variation

### Detail Noise
Adds an additional layer of fine-scale noise for subtle variation.  
Useful for breaking up repetitive patterns.

---

### Detail Strength
Controls how strongly the detail noise affects the terrain.

---

### Detail Scale
Adjusts the scale of the detail noise pattern.

---

## Mesh Controls

### Apply Subdivision
Automatically subdivides the base grid for smoother terrain results.

---

### Smooth Shading
Enables smooth shading for more natural lighting transitions across the terrain surface.

---

### Auto Normalize
Ensures terrain elevation fits within a consistent height range for export or texture baking.

---

## Material Options

### Apply Material
Automatically assigns a procedural material with color gradients based on height.

---

### Color Low
Defines the color used for the lowest altitude (valleys or water zones).

---

### Color High
Defines the color used for the highest altitude (mountain peaks).

---

### Material Blend
Controls the blending smoothness between low and high altitude colors.

---

## Operators

### Generate Terrain
Creates or updates the procedural landscape using the current settings.  
Automatically replaces the previous terrain if it was generated by the same tool.

---

### Apply Erosion Simulation
Applies the erosion algorithm on the active terrain mesh to refine geological realism.

---

### Reset Settings
Restores all generator parameters to their default values.

---

### Delete Terrain
Deletes the currently selected generated terrain object.

---

## Usage Notes

- Start by adjusting **Size**, **Height**, and **Resolution** to set the terrain scale.  
- Choose a **Noise Type** and fine-tune **Noise Scale**, **Octaves**, and **Lacunarity** for shape complexity.  
- Use **Erosion** controls to achieve natural weathered formations.  
- Apply **Surface Variation** for subtle randomness or stylized landscapes.  
- Materials and colors are optional visual helpers — they do not affect geometry.  
- The generated mesh is fully editable, UV-ready, and can be sculpted or displaced for further refinement.
