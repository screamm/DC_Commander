# DC Commander Themes

This directory contains theme definitions for DC Commander. Each theme is a JSON file that defines the color palette used throughout the application.

## Available Themes

### Norton Commander (norton_commander.json)
Classic retro blue theme inspired by the original Norton Commander.
- **Style**: Retro, nostalgic
- **Primary Color**: Deep Blue (#0000AA)
- **Best For**: Classic DOS enthusiasts

### Modern Dark (modern_dark.json)
Contemporary dark theme with modern blue accents.
- **Style**: Modern, clean
- **Primary Color**: Dodger Blue (#1E90FF)
- **Best For**: Long coding sessions, reduced eye strain

### Solarized (solarized.json)
Professional Solarized Dark color scheme.
- **Style**: Professional, sophisticated
- **Primary Color**: Solarized Blue (#268BD2)
- **Best For**: Precision work, accessibility

## Creating Custom Themes

### Quick Start

1. Copy an existing theme file
2. Rename it to `your_theme_name.json`
3. Edit the colors
4. Restart DC Commander
5. Press `Ctrl+T` to cycle to your theme

### Theme File Structure

```json
{
  "name": "your_theme_name",
  "display_name": "Your Theme Name",
  "primary": "#0066CC",
  "accent": "#00CCFF",
  "surface": "#001122",
  "panel": "#002244",
  "text": "#FFFFFF",
  "text_muted": "#888888",
  "warning": "#FFAA00",
  "error": "#FF4444",
  "success": "#44FF44",
  "selection": "#0066CC",
  "selection_text": "#FFFFFF"
}
```

### Color Properties

| Property | Description | Used For |
|----------|-------------|----------|
| `name` | Theme identifier (no spaces) | Internal reference |
| `display_name` | Human-readable name | UI display |
| `primary` | Primary accent color | Active borders, highlights |
| `accent` | Secondary accent color | Inactive borders |
| `surface` | Main background | Application background |
| `panel` | Panel background | File panels, dialogs |
| `text` | Primary text color | Main text, file names |
| `text_muted` | Secondary text color | Metadata, hints |
| `warning` | Warning color | Warning messages |
| `error` | Error color | Error messages |
| `success` | Success color | Success messages |
| `selection` | Selection highlight | Selected items |
| `selection_text` | Selection text | Text in selected items |

### Color Format Support

#### Hex Colors (Recommended)
```json
"primary": "#0066CC"      // 6-digit hex
"accent": "#0CF"           // 3-digit hex (shorthand)
"warning": "#FFAA00FF"     // 8-digit hex (with alpha)
```

#### Named Colors
```json
"text": "white"
"surface": "black"
"error": "red"
```

#### RGB/RGBA
```json
"primary": "rgb(0, 102, 204)"
"accent": "rgba(0, 204, 255, 0.8)"
```

#### HSL/HSLA
```json
"primary": "hsl(210, 100%, 40%)"
"accent": "hsla(187, 100%, 50%, 0.8)"
```

## Design Guidelines

### Contrast Requirements

Ensure sufficient contrast for readability:
- **Text on Surface**: Minimum 4.5:1 contrast ratio
- **Text on Selection**: Minimum 4.5:1 contrast ratio
- **Borders**: Visible against surface and panels

### Color Psychology

Choose colors that match your workflow:
- **Cool Colors** (blue, cyan): Professional, calm, focus
- **Warm Colors** (orange, yellow): Energy, creativity, warmth
- **Neutral Colors** (gray): Balanced, sophisticated, minimal

### Recommended Palettes

#### High Contrast Dark
```json
{
  "surface": "#000000",
  "panel": "#1A1A1A",
  "text": "#FFFFFF",
  "primary": "#00FF00",
  "accent": "#FFFF00"
}
```

#### Low Contrast Dark
```json
{
  "surface": "#2A2A2A",
  "panel": "#353535",
  "text": "#D0D0D0",
  "primary": "#4A90E2",
  "accent": "#7AB8E8"
}
```

#### Light Theme
```json
{
  "surface": "#FFFFFF",
  "panel": "#F5F5F5",
  "text": "#000000",
  "primary": "#0066CC",
  "accent": "#0099FF"
}
```

## Testing Your Theme

### Validation Checklist

- [ ] All 13 color properties defined
- [ ] Colors use valid format (hex, named, rgb, hsl)
- [ ] `name` field uses snake_case (no spaces)
- [ ] `display_name` is human-readable
- [ ] Text readable on surface background
- [ ] Text readable on selection background
- [ ] Primary color distinct from surface
- [ ] Error color clearly indicates danger
- [ ] Success color clearly indicates success
- [ ] Warning color clearly indicates caution

### Visual Testing

1. Start DC Commander
2. Navigate through directories
3. Select files
4. Trigger warnings/errors (try deleting non-existent file)
5. Check all UI elements are readable
6. Verify colors match your expectations

## Troubleshooting

### Theme Not Appearing

**Problem**: Custom theme doesn't show up when pressing Ctrl+T

**Solutions**:
- Ensure file is in `features/themes/` directory
- Verify file has `.json` extension
- Check JSON is valid (use JSON validator)
- Restart DC Commander

### Invalid Theme Error

**Problem**: "Invalid theme file" notification

**Solutions**:
- Validate JSON syntax (use jsonlint.com)
- Ensure all 13 color properties are present
- Check color formats are valid
- Review console output for specific errors

### Colors Not Applying

**Problem**: Theme loads but colors look wrong

**Solutions**:
- Restart DC Commander (required for CSS updates)
- Verify hex colors start with `#`
- Check contrast ratios for readability
- Test in different terminal emulators

### Theme Validation Failed

**Problem**: "Theme validation failed" notification

**Solutions**:
- Check all required fields present
- Verify color formats are valid
- Remove any extra/unknown fields
- Match structure of example themes

## Advanced Customization

### Per-Component Themes

Future feature: Different themes for different panels

```json
{
  "name": "mixed_theme",
  "display_name": "Mixed Theme",
  "left_panel": {
    "primary": "#0000AA",
    "surface": "#000055"
  },
  "right_panel": {
    "primary": "#AA0000",
    "surface": "#550000"
  }
}
```

### Dynamic Theme Properties

Future feature: Time-based theme switching

```json
{
  "name": "auto_theme",
  "display_name": "Auto Theme",
  "day_theme": "modern_dark",
  "night_theme": "solarized",
  "switch_time": "18:00"
}
```

## Sharing Themes

### Export Your Theme

1. Copy your theme JSON file
2. Share via GitHub Gist, Pastebin, etc.
3. Include preview screenshot
4. Document inspiration/use case

### Import Others' Themes

1. Download theme JSON file
2. Place in `features/themes/` directory
3. Restart DC Commander
4. Press Ctrl+T to cycle to new theme

## Theme Gallery

Share your themes! Create a GitHub discussion with:
- Theme name and file
- Screenshot of DC Commander with your theme
- Description of style/inspiration
- Best use cases

## Support

Having issues with themes?
- Check console output for errors
- Review validation checklist above
- Compare with working example themes
- Ask in GitHub issues with theme file attached

---

**Happy theming!** 🎨
