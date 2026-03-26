# Requirements Document

## Introduction

This feature extends the IaCreator diagram editor canvas with a richer set of interactive objects beyond the existing AWS service nodes. The canvas will support two categories of objects: architecture blocks (representing AWS services, already partially implemented) and common drawing objects (lines/arrows, geometric shapes). All objects will be resizable and clickable. Clicking an object opens a bottom panel with a tabbed interface: one tab for configuring Terraform variables (for architecture blocks) and one tab for configuring the visual appearance of the object. This lays the groundwork for a fully interactive architecture diagramming experience where users can annotate, group, and visually organize their infrastructure designs.

## Glossary

- **Canvas**: The infinite pan/zoom drawing surface where all diagram objects are rendered
- **Canvas_Object**: Any interactive item placed on the Canvas, including Architecture_Blocks and Common_Objects
- **Architecture_Block**: A Canvas_Object representing an AWS service (e.g., Lambda, S3, DynamoDB) that maps to a Terraform resource
- **Common_Object**: A Canvas_Object used for visual annotation that does not map to a Terraform resource (e.g., lines, arrows, geometric shapes)
- **Line_Object**: A Common_Object representing a straight line or arrow between two points on the Canvas
- **Geometric_Object**: A Common_Object representing a geometric shape (e.g., rectangle, ellipse) placed on the Canvas
- **Bottom_Panel**: The fixed panel at the bottom of the screen that opens when a Canvas_Object is selected (already exists as ConfigPanel)
- **Terraform_Tab**: A tab within the Bottom_Panel that displays Terraform variable configuration for an Architecture_Block
- **Visual_Tab**: A tab within the Bottom_Panel that displays visual appearance configuration for any Canvas_Object
- **Resize_Handle**: A draggable control point on the edges or corners of a selected Canvas_Object used to change its dimensions
- **Object_Bounds**: The width and height of a Canvas_Object on the Canvas
- **Visual_Config**: The set of visual appearance properties for a Canvas_Object (e.g., color, border, fill, stroke style)
- **Diagram_Store**: The Zustand state store that manages all diagram state including elements, connectors, and viewport

## Requirements

### Requirement 1: Canvas Object Type System

**User Story:** As a user, I want the canvas to support different types of objects (architecture blocks, lines, and geometric shapes), so that I can create rich, annotated architecture diagrams.

#### Acceptance Criteria

1. THE Canvas SHALL support three categories of Canvas_Objects: Architecture_Blocks, Line_Objects, and Geometric_Objects
2. WHEN a Canvas_Object is created, THE Diagram_Store SHALL assign a unique identifier and store the object category alongside its properties
3. THE Canvas SHALL render Architecture_Blocks with their AWS service icon and name label
4. THE Canvas SHALL render Line_Objects as straight lines between two endpoint positions
5. THE Canvas SHALL render Geometric_Objects as the specified shape (rectangle or ellipse) at the specified position and dimensions

### Requirement 2: Object Placement on Canvas

**User Story:** As a user, I want to place different types of objects on the canvas, so that I can build my architecture diagram with both service blocks and visual annotations.

#### Acceptance Criteria

1. WHEN the user selects an AWS service from the service picker and clicks on the Canvas, THE Canvas SHALL place a new Architecture_Block at the clicked position
2. WHEN the user selects the line tool and clicks two points on the Canvas, THE Canvas SHALL create a new Line_Object connecting those two points
3. WHEN the user selects a geometric shape tool and clicks on the Canvas, THE Canvas SHALL place a new Geometric_Object with default dimensions at the clicked position
4. WHEN a Canvas_Object is placed, THE Diagram_Store SHALL record the object with default Visual_Config values appropriate to its category

### Requirement 3: Object Selection and Click Interaction

**User Story:** As a user, I want to click on any canvas object to select it and see its configuration options, so that I can inspect and modify objects.

#### Acceptance Criteria

1. WHEN the user clicks on a Canvas_Object, THE Canvas SHALL visually indicate the object is selected by displaying a highlighted border
2. WHEN the user clicks on a Canvas_Object, THE Bottom_Panel SHALL open and display configuration tabs for the selected object
3. WHEN the user clicks on an empty area of the Canvas, THE Canvas SHALL deselect the currently selected Canvas_Object and close the Bottom_Panel
4. THE Canvas SHALL allow only one Canvas_Object to be selected at a time
5. WHEN a Canvas_Object is selected, THE Canvas SHALL display Resize_Handles on the object boundaries

### Requirement 4: Object Resizing

**User Story:** As a user, I want to resize objects on the canvas by dragging their edges or corners, so that I can adjust the visual layout of my diagram.

#### Acceptance Criteria

1. WHEN a Canvas_Object is selected, THE Canvas SHALL display Resize_Handles at the corners and midpoints of the Object_Bounds
2. WHEN the user drags a Resize_Handle, THE Canvas SHALL update the Object_Bounds of the Canvas_Object in real time to match the drag position
3. WHEN the user releases a Resize_Handle, THE Diagram_Store SHALL persist the new Object_Bounds
4. THE Canvas SHALL enforce a minimum width of 40 pixels and a minimum height of 40 pixels for all Canvas_Objects
5. WHEN the user resizes a Line_Object, THE Canvas SHALL move the corresponding endpoint to the new drag position
6. WHEN the user resizes an Architecture_Block, THE Canvas SHALL scale the block container while keeping the icon and label centered

### Requirement 5: Bottom Panel Tabbed Interface

**User Story:** As a user, I want the bottom panel to have tabs so I can switch between Terraform configuration and visual configuration for the selected object.

#### Acceptance Criteria

1. WHEN an Architecture_Block is selected, THE Bottom_Panel SHALL display two tabs: the Terraform_Tab and the Visual_Tab
2. WHEN a Common_Object is selected, THE Bottom_Panel SHALL display only the Visual_Tab
3. WHEN the Bottom_Panel opens, THE Bottom_Panel SHALL activate the first available tab by default
4. WHEN the user clicks a tab header, THE Bottom_Panel SHALL switch to display the content of the clicked tab
5. THE Bottom_Panel SHALL visually distinguish the active tab from inactive tabs using a highlighted style

### Requirement 6: Terraform Configuration Tab

**User Story:** As a user, I want to configure Terraform variables for architecture blocks, so that I can define the infrastructure properties of each AWS service.

#### Acceptance Criteria

1. WHEN the Terraform_Tab is active for a selected Architecture_Block, THE Bottom_Panel SHALL display the service-specific configuration form for that block's AWS service type
2. WHEN the user modifies a Terraform variable field, THE Diagram_Store SHALL update the corresponding config property on the Architecture_Block
3. THE Terraform_Tab SHALL display configuration fields appropriate to the selected service type (e.g., handler and runtime for Lambda, hash_key for DynamoDB)
4. IF the user enters an invalid value in a configuration field, THEN THE Terraform_Tab SHALL display a validation message adjacent to the field

### Requirement 7: Visual Configuration Tab for Architecture Blocks

**User Story:** As a user, I want to configure the visual appearance of architecture blocks, so that I can customize how service nodes look on the diagram.

#### Acceptance Criteria

1. WHEN the Visual_Tab is active for a selected Architecture_Block, THE Bottom_Panel SHALL display a width field and a height field for the Object_Bounds
2. WHEN the user changes the width or height value, THE Diagram_Store SHALL update the Object_Bounds of the Architecture_Block and the Canvas SHALL re-render the block at the new size
3. THE Visual_Tab SHALL enforce the minimum dimension constraint of 40 pixels for both width and height

### Requirement 8: Visual Configuration Tab for Line Objects

**User Story:** As a user, I want to configure the visual properties of lines and arrows, so that I can customize connectors and annotations on my diagram.

#### Acceptance Criteria

1. WHEN the Visual_Tab is active for a selected Line_Object, THE Bottom_Panel SHALL display controls for: color, border width, stroke style (solid or dashed), start arrow toggle, and end arrow toggle
2. WHEN the user changes the color value, THE Diagram_Store SHALL update the Line_Object color and the Canvas SHALL re-render the line in the new color
3. WHEN the user toggles the start arrow or end arrow, THE Diagram_Store SHALL update the Line_Object arrow configuration and the Canvas SHALL render or remove the arrowhead on the corresponding end
4. WHEN the user selects a dashed stroke style, THE Canvas SHALL render the Line_Object with a dashed pattern
5. WHEN the user changes the border width, THE Canvas SHALL render the Line_Object with the specified stroke width

### Requirement 9: Visual Configuration Tab for Geometric Objects

**User Story:** As a user, I want to configure the visual properties of geometric shapes, so that I can use them as grouping boxes, labels, or decorative elements.

#### Acceptance Criteria

1. WHEN the Visual_Tab is active for a selected Geometric_Object, THE Bottom_Panel SHALL display controls for: width, height, fill toggle, fill color, border color, border width, and shape type (rectangle or ellipse)
2. WHEN the user toggles fill on, THE Canvas SHALL render the Geometric_Object with a filled interior using the specified fill color
3. WHEN the user toggles fill off, THE Canvas SHALL render the Geometric_Object with only its border (no fill)
4. WHEN the user changes the border color, THE Canvas SHALL re-render the Geometric_Object border in the new color
5. WHEN the user changes the shape type, THE Canvas SHALL re-render the Geometric_Object as the newly selected shape
6. THE Visual_Tab SHALL enforce the minimum dimension constraint of 40 pixels for both width and height of Geometric_Objects

### Requirement 10: Visual Config Persistence in Diagram State

**User Story:** As a user, I want my visual configuration changes to be saved and restored when I save and load diagrams, so that I do not lose my customizations.

#### Acceptance Criteria

1. WHEN the user saves a diagram, THE Diagram_Store SHALL serialize all Visual_Config properties for every Canvas_Object into the diagram state
2. WHEN the user loads a diagram, THE Diagram_Store SHALL deserialize Visual_Config properties and apply them to each Canvas_Object
3. FOR ALL valid Visual_Config objects, serializing then deserializing SHALL produce an equivalent Visual_Config object (round-trip property)

### Requirement 11: Object Deletion

**User Story:** As a user, I want to delete any canvas object, so that I can remove objects I no longer need from my diagram.

#### Acceptance Criteria

1. WHEN a Canvas_Object is selected and the user presses the Delete key, THE Diagram_Store SHALL remove the Canvas_Object from the diagram
2. WHEN a Canvas_Object is selected and the user clicks the delete button in the Bottom_Panel, THE Diagram_Store SHALL remove the Canvas_Object from the diagram
3. WHEN an Architecture_Block is deleted, THE Diagram_Store SHALL also remove all connectors attached to that block
4. WHEN a Canvas_Object is deleted, THE Bottom_Panel SHALL close
