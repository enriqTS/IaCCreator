# Requirements: Canvas Objects Editor (v2)

## Requirement 1: Architecture Block Icon-First Rendering

**User Story:** As a diagram author, I want architecture blocks to render with the AWS service icon as the primary visual element that scales with the block dimensions, so that my diagrams look clean and icon-centric.

### Acceptance Criteria

1. WHEN an architecture block is rendered THEN the system SHALL display the AWS service icon as the primary visual element, scaling it to fill the block dimensions (with padding)
2. WHEN an architecture block has no service name defined (empty or default) THEN the system SHALL display only the icon without a label
3. WHEN an architecture block has a user-defined service name THEN the system SHALL display the name label below the icon
4. WHEN an architecture block is resized THEN the icon SHALL scale proportionally with the block dimensions
5. WHEN an architecture block icon is rendered THEN the icon SHALL maintain its aspect ratio regardless of block dimensions

## Requirement 2: Unified Line/Arrow Type with Connection Anchors

**User Story:** As a diagram author, I want a single line/arrow object type that supports connection anchors on other objects, so that I can create connected diagrams with lines that snap to object edges.

### Acceptance Criteria

1. WHEN a line object is created THEN the system SHALL support optional sourceAnchor and targetAnchor fields referencing other canvas objects
2. WHEN a line endpoint is near an object edge (within snap threshold) THEN the system SHALL snap the endpoint to the nearest anchor point on that object
3. WHEN a connected object is moved THEN the system SHALL update the anchored line endpoints to follow the object's new position
4. WHEN an anchor point is computed THEN the system SHALL calculate it as the intersection of the line direction with the object's bounding rectangle
5. WHEN a line has both startArrow and endArrow set THEN the system SHALL render arrowheads at both endpoints
6. WHEN a connected object is deleted THEN the system SHALL detach the line endpoint (convert to absolute position) rather than deleting the line

## Requirement 3: Pull-to-Connect from Object Edges

**User Story:** As a diagram author, I want to drag from the edge of any object to create a new connected line, so that I can quickly wire objects together.

### Acceptance Criteria

1. WHEN the pointer hovers near the edge of a canvas object THEN the system SHALL display connection anchor indicators (small circles at cardinal points)
2. WHEN the user drags from an anchor indicator THEN the system SHALL begin creating a new line with the source anchored to that object
3. WHEN the drag ends over another object's anchor zone THEN the system SHALL complete the line with the target anchored to that object
4. WHEN the drag ends over empty canvas THEN the system SHALL create a line with a free (unanchored) endpoint at the drop position
5. WHEN pull-to-connect is active THEN the system SHALL show a preview line from the source anchor to the cursor position

## Requirement 4: Text Object with Double-Click Creation

**User Story:** As a diagram author, I want to create text labels by double-clicking on the canvas and typing, so that I can annotate my diagrams with free-form text.

### Acceptance Criteria

1. WHEN the user double-clicks on empty canvas (with pointer tool active) THEN the system SHALL create a new text object at that position and enter inline editing mode
2. WHEN a text object is in editing mode THEN the system SHALL display an editable text input at the object's position
3. WHEN the user presses Escape or clicks outside during editing THEN the system SHALL commit the text and exit editing mode
4. WHEN a text object's content is empty after editing THEN the system SHALL remove the text object automatically
5. WHEN a text object is rendered THEN the system SHALL display it with configurable font size, color, and alignment
6. WHEN a text object is selected THEN the system SHALL show resize handles and allow repositioning
7. WHEN the user double-clicks an existing text object THEN the system SHALL re-enter inline editing mode for that object

## Requirement 5: Expanded Geometric Shapes (25+ Shapes)

**User Story:** As a diagram author, I want access to a wide variety of geometric shapes beyond rectangle and ellipse, so that I can create rich, expressive diagrams.

### Acceptance Criteria

1. WHEN the shape picker is opened THEN the system SHALL display at least 25 geometric shape options organized by category
2. WHEN a shape is selected from the picker THEN the system SHALL activate the place-shape tool for that specific shape variant
3. WHEN a geometric object is rendered THEN the system SHALL draw the correct SVG path for its shape variant
4. WHEN a geometric object is resized THEN the SVG path SHALL scale proportionally within the new bounding box
5. WHEN the shape list is defined THEN it SHALL include at minimum: rectangle, rounded-rectangle, ellipse, circle, triangle, diamond, parallelogram, trapezoid, hexagon, octagon, pentagon, star, cross, arrow-right, arrow-left, arrow-up, arrow-down, chevron, cylinder, cloud, callout, document, process, decision, data, predefined-process

## Requirement 6: UML Objects

**User Story:** As a diagram author, I want to place UML diagram elements (class, interface, actor, use case, component, package, node), so that I can create UML diagrams.

### Acceptance Criteria

1. WHEN a UML object type is selected from the picker THEN the system SHALL create a UML-specific canvas object with the correct visual representation
2. WHEN a UML class object is rendered THEN the system SHALL display it with three compartments: name, attributes, and methods
3. WHEN a UML interface object is rendered THEN the system SHALL display it with a «interface» stereotype label and method compartment
4. WHEN a UML actor object is rendered THEN the system SHALL display the stick-figure icon with a name label below
5. WHEN a UML use case object is rendered THEN the system SHALL display it as an ellipse with centered text
6. WHEN a UML component object is rendered THEN the system SHALL display it as a rectangle with the component icon (two small rectangles on the left edge)
7. WHEN a UML package object is rendered THEN the system SHALL display it as a tabbed rectangle with the package name in the tab
8. WHEN a UML node object is rendered THEN the system SHALL display it as a 3D box (cube perspective)
9. WHEN a UML class or interface is edited THEN the system SHALL allow adding/removing attributes and methods through the config panel

## Requirement 7: Categorized Object Picker Menu

**User Story:** As a diagram author, I want a categorized picker menu in the toolbar that organizes all available objects (AWS services, shapes, UML elements, text) into browsable categories, so that I can quickly find and place any object type.

### Acceptance Criteria

1. WHEN the object picker is opened THEN the system SHALL display categories: AWS Services, Geometric Shapes, UML Elements, and Annotations
2. WHEN a category is selected THEN the system SHALL display the objects within that category as a grid or list with icons and labels
3. WHEN the user searches in the picker THEN the system SHALL filter objects across all categories matching the search term
4. WHEN an object is selected from the picker THEN the system SHALL activate the appropriate placement tool for that object type
5. WHEN the picker is displayed THEN each object SHALL show a preview icon or thumbnail representing its visual appearance

## Requirement 8: Connection State Persistence

**User Story:** As a diagram author, I want line connections (anchors) to be saved and restored when I save/load a diagram, so that my connected diagrams persist correctly.

### Acceptance Criteria

1. WHEN a diagram with anchored lines is serialized THEN the system SHALL include sourceAnchor and targetAnchor object references in the serialized line data
2. WHEN a diagram with anchored lines is deserialized THEN the system SHALL restore the anchor references and recompute anchor positions
3. WHEN a referenced anchor target no longer exists in the loaded diagram THEN the system SHALL gracefully degrade the endpoint to an absolute position

## Requirement 9: Serialization for All New Types

**User Story:** As a diagram author, I want all new object types (text, expanded shapes, UML elements) to be saved and loaded correctly, so that my diagrams persist completely.

### Acceptance Criteria

1. WHEN a diagram containing text objects is serialized THEN the system SHALL include all text content, font size, color, alignment, and position data
2. WHEN a diagram containing expanded geometric shapes is serialized THEN the system SHALL include the specific shape variant identifier
3. WHEN a diagram containing UML objects is serialized THEN the system SHALL include all UML-specific data (compartments, attributes, methods, stereotypes)
4. WHEN a serialized diagram is loaded THEN the system SHALL reconstruct all object types with their full visual and data state
5. WHEN serializing any canvas object THEN the system SHALL produce valid JSON that round-trips without data loss
6. WHEN loading a diagram saved with the previous version (v2) THEN the system SHALL migrate it to v3 format, preserving all existing objects and adding defaults for new fields

## Requirement 10: Architecture and Maintainability

**User Story:** As a developer, I want the canvas object system to be well-organized with clear separation of concerns, so that new object types can be added easily in the future.

### Acceptance Criteria

1. WHEN a new object type is added THEN the developer SHALL only need to add a type variant, a renderer component, and a config panel entry
2. WHEN the type system is extended THEN the discriminated union pattern SHALL be maintained for type safety
3. WHEN rendering components are organized THEN each object type SHALL have its own dedicated renderer component
