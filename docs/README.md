
## Project Role in KI Ecosystem

yaml-cfg-wizard is designed to be **app-agnostic** and reusable. It provides:

- Generic YAML config management
- Schema validation and scaffolding
- Layered config resolution
- CLI tools for config operations

### What It Does NOT Include

- Application-specific features (prompts, AI settings, etc.)
- App-specific CLI commands
- Business logic beyond config management

### Use in Other Projects

When creating a new application:

1. Use yaml-cfg-wizard for config infrastructure
2. Add app-specific schemas via schema extension
3. Implement app-specific features in the application project
4. Use yaml-cfg-wizard CLI for generic config operations

This maintains clean separation of concerns and makes yaml-cfg-wizard reusable across projects.

### Example: kicli-code-assist Integration

kicli-code-assist uses yaml-cfg-wizard for:
- Loading and merging YAML configurations
- Validating configs against schemas
- Providing generic scaffold/validate/merge commands

But implements in its own project:
- Prompt Management feature
- Security settings
- Custom CLI commands for prompts, security, etc.

