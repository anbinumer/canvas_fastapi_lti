# QA Automation LTI Tool Product Requirements Document (PRD)

## Goals and Background Context

### Goals
- Create a robust, reusable LTI framework that can house various automation tasks (starting with QA)
- Eliminate iframe compatibility issues and ensure seamless Canvas LMS integration  
- Enable Learning Technologists (vibe coders) to build LTI tools using AI coding assistants
- Provide Learning Designers with intuitive, minimal-input interfaces for QA automation
- Establish human-centered design patterns following modern AI interface principles
- Deliver MVP with find-and-replace QA automation using existing script
- Create scalable foundation for future automation tasks beyond QA

### Background Context

Currently, QA automation tasks rely on rule-based Python scripts executed locally via terminal - a process that's inconvenient and inaccessible to the broader Learning Design team. Rather than distributing scripts individually, this project creates an LTI framework that centralizes these capabilities within Canvas LMS where Learning Designers already work.

The project addresses two critical needs: streamlining QA workflows for immediate productivity gains, and establishing a reusable LTI development pattern that Learning Technologists can leverage for future automation projects using AI coding tools. The design philosophy embraces the interface patterns research from H2A.dev, particularly the principle that effective AI interfaces should adapt to user expertise levels - simple for end users, powerful for builders.

### Change Log
| Date | Version | Description | Author |
|------|---------|-------------|---------|
| [Current Date] | 1.0 | Initial PRD creation | PM Agent |

## Requirements

### Functional Requirements
1. **FR1**: LTI tool integrates seamlessly with Canvas LMS without iframe compatibility issues
2. **FR2**: LTI tool receives and processes Canvas launch parameters for automatic authentication and context
3. **FR3**: Find-and-replace automation executes using provided Python script  
4. **FR4**: User provides minimal input (find text, replace text, scope) via intuitive interface
5. **FR5**: System generates dashboard with QA results and actionable recommendations
6. **FR6**: Framework architecture supports adding additional QA automation tasks **limited to Canvas API endpoint availability**
7. **FR7**: Interface follows ACU brand styling (Deep Purple #4A1A4A, ACU Red #D2492A, Gold #F4B942)

### Non-Functional Requirements
1. **NFR1**: Built using FastAPI framework as specified
2. **NFR2**: Interface designed for non-technical Learning Designers
3. **NFR3**: Code structure supports Learning Technologists using AI coding tools
4. **NFR4**: Response time under 30 seconds for typical QA operations
5. **NFR5**: Secure handling of Canvas API credentials and user data
6. **NFR6**: 99% availability during standard business hours (8am-6pm AEST)
7. **NFR7**: Automatic backup of QA task configurations and results to Railway persistent storage
8. **NFR8**: System monitoring with alerts for LTI authentication failures and Canvas API errors
9. **NFR9**: Graceful degradation when Canvas API is unavailable
10. **NFR10**: WCAG AA color contrast compliance (minimum 4.5:1 ratio)

## User Interface Design Goals

### Overall UX Vision
**Clean, minimal interface** that feels native within Canvas LMS. Learning Designers should be able to accomplish QA tasks with **3 clicks or less**: select task type → provide inputs → view results. The interface should feel like a natural extension of Canvas rather than an external tool, following the **"Chat on a Webpage"** pattern from H2A research - familiar interactions enhanced with powerful automation.

### Key Interaction Paradigms
- **Task Selection**: Simple dropdown or card-based selection of QA automation tasks
- **Input Forms**: Minimal, contextual forms with smart defaults and clear labels  
- **Results Dashboard**: Visual, scannable reports with actionable insights highlighted
- **Progressive Disclosure**: Show only what's needed for current step, reveal complexity gradually
- **One-Click Actions**: Execute QA tasks with single button press after minimal setup

### Core Screens and Views
1. **Task Selection Screen**: Choose QA automation type (starting with Find & Replace)
2. **Configuration Screen**: Minimal input form for task parameters  
3. **Execution Screen**: Progress indicator and real-time feedback
4. **Results Dashboard**: Visual report with findings, recommendations, and export options
5. **Framework Admin** (future): Interface for Learning Technologists to add new QA tasks

### Accessibility: WCAG AA
Canvas LMS standard compliance - sufficient color contrast ratios for accessibility.

### Branding 
**ACU Brand Integration**:
- Primary: Deep Purple (#4A1A4A) for headers and primary actions
- Background: #6B2C6B for main text and interface elements
- Actions: ACU Red (#D2492A, #B8391F) for buttons and interactive elements  
- Highlights: Gold (#F4B942, #E6A830) for success states and secondary actions
- Content: Cream/Light (#F9F4F1, #F4ECE6) for content backgrounds and cards

### Target Device and Platforms: Web Responsive
Canvas LMS integration primarily desktop/laptop focused, but responsive design for tablet access.

## Technical Assumptions

### Repository Structure: Monorepo
Single repository containing LTI framework, QA automation scripts, and documentation - ideal for Learning Technologists using AI coding tools.

### Service Architecture 
**FastAPI Monolith with Modular QA Tasks** - Single FastAPI application with pluggable QA automation modules. Clean separation allows easy addition of new QA tasks while maintaining simple deployment model.

### Testing Requirements
**Unit + Integration Testing** - Essential for LTI reliability. Unit tests for individual QA scripts, integration tests for Canvas LTI launch flow and API interactions.

### Additional Technical Assumptions and Requests

**LTI Integration Stack:**
- FastAPI framework (as specified)
- LTI 1.3 Advantage standard for Canvas compatibility  
- PyLTI1p3 library for LTI authentication handling
- Canvas API integration for course content access

**QA Automation Architecture:**
- Modular script framework allowing easy addition of new QA tasks
- Existing Python find-and-replace script as first module
- Standardized input/output interface for all QA modules
- Asynchronous execution for long-running QA operations

**Development & Deployment:**
- **GitHub** for source control and collaboration
- **Railway** for hosting and deployment (automatic deployments from main branch)
- Environment-based configuration via Railway's environment variables
- Simple workflow: code in Cursor → commit to GitHub → auto-deploy to Railway

**Canvas Integration Requirements:**
- Deep linking support for seamless Canvas navigation
- Course context preservation throughout QA workflows
- Grade passback capability (future enhancement)
- Content Security Policy compliance for iframe embedding

## Cross-Functional Requirements

### Data Requirements
- **Canvas API Data**: Course content (syllabus, pages, assignments, quizzes, discussions, announcements, modules)
- **User Context Data**: LTI launch parameters (user ID, name, roles, course ID, Canvas instance URL)
- **QA Task Data**: Task configurations (URL mappings, scope parameters), execution results, timestamps
- **Session Data**: LTI authentication state, user preferences, task history
- **Storage Requirements**: Task results stored for 90 days, user configurations indefinitely
- **Data Privacy**: No Canvas content stored permanently, only processed in memory during QA execution
- **Data Format**: JSON for task configurations and results, structured logging for audit trails

### Integration Requirements
- **Canvas LTI 1.3**: Deep linking, resource selection, and grade passback capability architecture
- **Canvas API v1**: Course content access using user's Canvas permissions via LTI context
- **Railway Platform**: Environment variable configuration, persistent volume for logs and temporary storage
- **GitHub Integration**: Automatic deployment triggers, version control for QA automation scripts
- **External Dependencies**: PyLTI1p3 library, FastAPI framework, BeautifulSoup HTML parsing
- **API Rate Limiting**: Canvas API throttling compliance (200 requests per minute per user)
- **Authentication Flow**: LTI launch → Canvas OAuth → API access token management

### Canvas API Constraints
- **Rate Limiting**: 200 requests/minute per user, 5,000 requests/hour per application, burst allowance of 50 requests
- **OAuth Token Expiry**: Access tokens expire after 1 hour, refresh tokens expire after 90 days
- **Pagination Requirements**: Most endpoints return max 100 items per page, requires link header navigation for large datasets
- **Permission Scope**: API access limited to user's Canvas permissions; LTI context doesn't guarantee full API access
- **Content Size Limits**: Large content items (>1MB) may require streaming or chunked retrieval
- **Concurrent Request Limits**: Maximum 10 concurrent requests per user to prevent server overload
- **Instance Variations**: Canvas cloud vs self-hosted instances may have different API configurations and rate limits
- **API Versioning**: Canvas API v1 specific behaviors - some endpoints deprecated, others with specific parameter requirements
- **Content Access Patterns**: Quiz questions, module items, and discussion replies require separate API calls beyond parent objects
- **Error Handling**: Canvas API returns specific error codes for rate limiting (429), authentication (401), permissions (403)
- **Response Format**: JSON responses with Canvas-specific metadata, timestamps in ISO 8601 format
- **Webhook Limitations**: Canvas doesn't provide real-time webhooks for content changes, requiring polling for updates
- **API Endpoint Coverage**: QA automation tasks are limited to Canvas-provided API endpoints only; no access to internal Canvas tools or non-API functionality
- **Available Endpoints**: Course content (syllabus, pages, assignments, quizzes, discussions, announcements, modules), user data, enrollment data, files
- **Unavailable Functionality**: Canvas's internal link checker, accessibility scanner, plagiarism detection settings, native analytics, backup/restore, migration tools, administrative configurations

### Operational Requirements
- **Deployment**: Blue-green deployment via Railway with zero-downtime releases
- **Environment Management**: Development, staging, production environments with separate Canvas instances
- **Monitoring**: Application logs, Canvas API response times, LTI launch success rates, error tracking
- **Alerting**: Email notifications for Canvas API failures, LTI authentication errors, system downtime
- **Support**: Logging framework for troubleshooting QA script failures and Canvas integration issues
- **Backup Strategy**: Daily backup of task configurations, weekly backup of execution logs
- **Performance Monitoring**: Track QA task execution times, Canvas API response times, user interface loading times

## Technical Risk Assessment

### High-Risk Areas
1. **LTI iframe Compatibility**: Canvas iframe restrictions may block JavaScript or CSS functionality
   - **Mitigation**: Early prototype testing, Content Security Policy compliance, fallback rendering modes

2. **Canvas API Rate Limiting**: Heavy QA operations may exceed 200 requests/minute or 5,000/hour limits, especially for large courses
   - **Mitigation**: Request throttling with exponential backoff, batch processing with progress tracking, API request queuing, user feedback on rate limit status

3. **Authentication Token Management**: OAuth tokens expire after 1 hour, potentially during long QA operations on large courses
   - **Mitigation**: Proactive token refresh at 50-minute mark, graceful session extension, progress preservation with resumable operations

4. **Canvas API Permission Scope**: User's LTI permissions may not match required API permissions for content access
   - **Mitigation**: Permission validation during LTI launch, clear error messages for insufficient access, graceful fallback for restricted content

5. **Cross-Canvas Instance Compatibility**: Different Canvas configurations may affect LTI behavior
   - **Mitigation**: Testing across multiple Canvas instances, configuration detection, adaptive rendering

### Medium-Risk Areas
6. **QA Script Integration**: Existing Python script may not adapt cleanly to LTI context
   - **Mitigation**: Thorough testing of CanvasURLScanner class adaptations, fallback error handling

7. **User Interface Complexity**: Learning Designers may find interface too complex despite design goals
   - **Mitigation**: User testing throughout development, progressive disclosure, contextual help

8. **Framework Extensibility**: Architecture may not support future QA tasks as seamlessly as planned
   - **Mitigation**: Abstract base class design, comprehensive documentation, plugin validation testing

9. **Canvas API Pagination Handling**: Large courses may require multiple API calls with complex pagination logic
   - **Mitigation**: Robust pagination handling with progress tracking, efficient cursor-based navigation, memory management for large datasets

10. **QA Task Scope Limitations**: Some desired QA automation tasks may not be possible due to Canvas API endpoint unavailability
    - **Mitigation**: Early discovery and documentation of available endpoints, clear communication about QA task limitations, focus on high-value API-accessible tasks

### Low-Risk Areas
11. **Railway Deployment**: Platform stability and performance sufficient for LTI application
12. **FastAPI Performance**: Framework capability adequate for expected user load and QA operations
13. **ACU Branding Integration**: Color palette and design system implementation straightforward

## Epic List

### Epic Structure for MVP

**Epic 1: Foundation & Core LTI Infrastructure**  
Establish FastAPI project with LTI 1.3 integration, Canvas authentication, and deliver a functional "Hello World" LTI that loads seamlessly within Canvas without iframe issues.

**Epic 2: Find & Replace QA Automation**  
Implement the first QA automation task using existing find-and-replace script, complete with intuitive UI following ACU branding and results dashboard for Learning Designers.

## MVP Success Criteria and Validation

### Success Metrics
- **Task Completion Time**: 90% reduction in QA setup time (from 15 minutes terminal setup to 2 minutes via LTI interface)
- **User Adoption**: 80% of Learning Designers complete at least one QA task within 2 weeks of MVP deployment
- **Technical Success**: 95% successful LTI launches without iframe compatibility issues
- **Accuracy**: 100% parity between existing Python script results and LTI implementation results
- **Usability**: Learning Designers can complete find-and-replace task without training or documentation

### MVP Validation Approach
1. **Technical Validation**: Deploy to Canvas LMS development instance and test with 3 different course types
2. **User Acceptance Testing**: 5 Learning Designers complete guided QA tasks using MVP interface
3. **Performance Testing**: Execute QA tasks on courses with 50+ content items to validate response times
4. **Integration Testing**: Verify LTI tool works across different Canvas course configurations
5. **Feedback Collection**: Post-task surveys measuring ease of use, time savings, and satisfaction
6. **Success Threshold**: MVP succeeds if 4/5 Learning Designers complete tasks successfully and report time savings

### Learning Goals for MVP
- Validate LTI integration complexity and iframe compatibility solutions
- Confirm user interface paradigms work for non-technical users
- Test framework architecture for adding future QA automation tasks
- Identify Canvas API rate limiting and performance considerations
- Gather feedback on ACU branding integration and visual design effectiveness

## Epic Details

### Epic 1: Foundation & Core LTI Infrastructure

**Epic Goal:** Establish a robust FastAPI application with complete LTI 1.3 integration that authenticates seamlessly with Canvas LMS and renders without iframe compatibility issues. This foundation provides the technical infrastructure and development patterns that Learning Technologists can extend for any future automation tasks, not just QA.

**Integration Requirements:** LTI 1.3 Advantage compliance, Canvas deep linking support, secure credential handling, and responsive UI framework with ACU branding system.

#### Story 1.1: FastAPI Project Setup & Basic Structure

As a **Learning Technologist**,  
I want **a properly configured FastAPI project with development environment**,  
so that **I can begin building LTI functionality with clear project structure**.

**Acceptance Criteria:**
1. FastAPI application initializes with project structure suitable for AI-assisted development
2. Development environment includes hot reload and debugging capabilities  
3. Basic routing structure established for LTI endpoints
4. Environment configuration system supports development/staging/production
5. GitHub repository initialized with appropriate .gitignore and README
6. Railway deployment configuration files created
7. Basic health check endpoint returns 200 status

#### Story 1.2: LTI 1.3 Authentication Integration

As a **Canvas LMS user**,  
I want **secure LTI authentication that works seamlessly**,  
so that **I can access the tool without manual login or security barriers**.

**Acceptance Criteria:**
1. PyLTI1p3 library integrated and configured for Canvas LTI 1.3
2. LTI launch endpoint processes Canvas authentication parameters correctly
3. User context (name, roles, course info) extracted from LTI launch
4. Session management maintains authentication state throughout tool usage
5. Invalid or expired LTI launches are handled gracefully with clear error messages
6. Security best practices implemented for credential storage and validation
7. Integration tested with Canvas LMS development instance

#### Story 1.3: Canvas Integration & UI Foundation

As a **Learning Designer**,  
I want **the LTI tool to feel native within Canvas with ACU branding**,  
so that **the interface is familiar and professionally integrated**.

**Acceptance Criteria:**
1. LTI tool renders correctly within Canvas iframe without compatibility issues
2. Responsive design works on desktop and tablet viewports
3. ACU color palette implemented: Deep Purple (#4A1A4A), ACU Red (#D2492A), Gold (#F4B942), Cream (#F9F4F1)
4. Color contrast ratios meet WCAG AA standards for accessibility
5. Basic navigation structure and layout components created
6. Tool integrates with Canvas breadcrumb navigation
7. Loading states and error handling follow Canvas UX patterns
8. "Hello World" dashboard displays user context and course information from LTI launch

### Epic 2: Find & Replace QA Automation

**Epic Goal:** Implement the first QA automation capability using the existing find-and-replace script, providing Learning Designers with an intuitive interface to execute QA tasks and view actionable results. This epic establishes the modular architecture pattern for adding future QA automation tasks.

**Integration Requirements:** Seamless integration of existing Python QA script, asynchronous task execution, comprehensive results reporting, and user-friendly task configuration.

#### Story 2.1: QA Task Framework Architecture

As a **Learning Technologist**,  
I want **a modular framework for QA automation tasks**,  
so that **I can easily add new QA scripts using AI coding assistance**.

**Acceptance Criteria:**
1. Abstract QA task base class defines standard interface for all automation tasks
2. Task registration system allows dynamic loading of QA automation modules
3. Standardized input/output format for task parameters and results
4. Asynchronous task execution system handles long-running QA operations
5. Task status tracking and progress reporting infrastructure
6. Error handling and logging framework for debugging QA script issues
7. Framework architecture documented for Learning Technologist reference

#### Story 2.2: Find & Replace QA Implementation

As a **Learning Designer**,  
I want **to execute find-and-replace URL scanning on my current course content**,  
so that **I can quickly identify and update URL consistency issues across all content types**.

**Acceptance Criteria:**
1. Existing CanvasURLScanner class adapted for single-course operation using LTI context
2. User interface accepts multiple URL mappings (old URL → new URL pairs)
3. Scanner processes all Canvas content types: syllabus, pages, assignments, quizzes, discussions, announcements, modules
4. **Real-time progress updates** show which content type is being processed
5. Canvas API calls use **LTI user context** instead of hardcoded API token
6. **BeautifulSoup HTML parsing** maintains existing functionality for proper URL detection
7. Findings list captures all replacements with timestamps and update status
8. **Concurrent processing** optimized for single-course scope (faster than subaccount processing)

#### Story 2.3: QA Results Dashboard & User Interface

As a **Learning Designer**,  
I want **an intuitive interface to configure QA tasks and view clear results**,  
so that **I can efficiently perform QA automation with minimal effort**.

**Acceptance Criteria:**
1. Task selection interface with clear description of find-and-replace functionality
2. Simple configuration form with find text, replace text, and scope options
3. One-click task execution with clear progress indicators
4. Results dashboard displays findings in scannable, visual format
5. Actionable recommendations highlighted for immediate attention
6. Export functionality for results (PDF or CSV format)
7. Task history shows previous executions with timestamps and parameters
8. Interface follows ACU branding and maintains Canvas integration UX patterns
9. Error states handled gracefully with clear user guidance

## Next Steps

### UX Expert Prompt

Please create the frontend architecture and design specifications for the QA Automation LTI Tool using this PRD as input. Focus on:

**Design Priorities:**
- Canvas-native interface that feels integrated, not external
- ACU brand implementation with accessibility compliance
- 3-click task completion workflow for Learning Designers
- Progressive disclosure hiding complexity from non-technical users

**Key Design Challenges:**
- LTI iframe constraints and responsive design within Canvas
- Real-time progress feedback for QA operations
- Visual results dashboard with actionable insights
- ACU color palette with WCAG AA contrast requirements

**Deliverables Needed:**
- Component library specification with ACU branding
- User flow diagrams for QA task execution
- Interface mockups for Task Selection, Configuration, Execution, and Results screens
- Canvas integration guidelines and iframe compatibility solutions

The goal is an interface that Learning Designers can use intuitively while maintaining the professional ACU brand experience within Canvas LMS.

### Architect Prompt

Please create the technical architecture document for the QA Automation LTI Tool using this PRD as input. Focus on:

**Architecture Priorities:**
- FastAPI + LTI 1.3 integration with Canvas LMS
- Modular QA task framework for easy expansion by Learning Technologists using AI coding tools
- Canvas API constraint handling (rate limiting, pagination, authentication)
- Railway deployment with GitHub integration

**Key Technical Challenges:**
- LTI authentication flow and Canvas API token management
- Asynchronous QA task execution with progress tracking
- Canvas API rate limiting (200/min, 5000/hour) and error handling
- Existing Python QA script integration (CanvasURLScanner class adaptation)

**Critical Constraints:**
- All QA automation limited to Canvas API endpoint availability
- Learning Technologists will use AI coding assistants for development
- Must handle Canvas cloud vs self-hosted instance variations
- Security best practices for Canvas API credentials and user data

**Deliverables Needed:**
- System architecture diagram with LTI flow
- Database schema for task configurations and results
- API design for QA task framework
- Deployment and monitoring strategy
- Integration patterns for future QA task additions

The goal is a robust, scalable architecture that enables both MVP delivery and future expansion while respecting all Canvas API constraints.