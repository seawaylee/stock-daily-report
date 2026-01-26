---
name: remotion_video_creator
description: Create, modify, and render programmatic videos using Remotion (React-based video creation).
---

# Remotion Video Creator

This skill enables the creation of programmatic videos using the Remotion framework. Remotion allows you to create videos using React components, making it ideal for data-driven video generation, automated reporting, and personalized content.

## Capabilities

1.  **Project Initialization**: Set up a new Remotion project structure.
2.  **Composition Management**: Create and modify video compositions (scenes, timelines).
3.  **Data Integration**: Inject dynamic data (e.g., stock data, JSON) into video templates.
4.  **Rendering**: Export videos to MP4 format programmatically or via CLI.

## Workflow

### 1. Prerequisites
- **Node.js**: Ensure Node.js is installed (`node -v`).
- **FFmpeg**: Remotion requires FFmpeg for rendering. It is usually downloaded automatically, but verify if needed.

### 2. Setup (New Project)
To initialize a new Remotion project within the current workspace:

```bash
npx create-remotion@latest ./remotion-video
```
*Note: Choose the "Blank" or "HelloWorld" template for a clean start.*

### 3. Development Structure
A standard Remotion project includes:
- `src/index.ts` (or `src/Root.tsx`): The entry point where `registerRoot` is called.
- `src/Composition.tsx`: The main video component.
- `package.json`: Dependencies.

### 4. Creating content
- **Use `useCurrentFrame()`**: Get the current frame number to drive animations.
- **Use `interpolate()`**: Map frame numbers to animation values (e.g., opacity, transform).
- **Use `staticFile()`**: Import assets from the `public/` folder.

### 5. Rendering
To render a video from the command line:

```bash
npx remotion render <EntryFile> <CompositionID> <OutputFile>
```

**Example:**
```bash
npx remotion render src/index.ts MyComp out.mp4
```

## Integration with Stock Report
To generate a daily stock report video:
1.  **Prepare Data**: Save daily stock data to a JSON file (e.g., `public/daily_data.json`).
2.  **Import Data**: In your Remotion component, import the JSON file.
3.  **Render**: Run the render command targeting a specific composition (e.g., `DailyReport`).

## Common Issues
- **Missing Dependencies**: Run `npm install` inside the `remotion-video` folder.
- **FFmpeg Errors**: Ensure permissions are correct or install FFmpeg globally if auto-download fails.
- **Memory Limits**: For long videos, increase Node memory limit (`NODE_OPTIONS="--max-old-space-size=4096"`).
