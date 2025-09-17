# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

APS智慧排产系统 (APS Tobacco v3) - An intelligent production scheduling system specifically designed for tobacco manufacturing. This system implements advanced scheduling algorithms to process Excel-based production plans, optimize machine allocation, and generate work orders for both packing machines (卷包机) and feeding machines (喂丝机).

**Key Focus**: The system is primarily designed for processing tobacco packaging production plans with complex business rules including merging, splitting, time correction, and parallel processing algorithms. The system now supports both decade plans and monthly plans with direct Excel scheduling capabilities.

**Monthly Plan Integration**: ✅ **NEW FEATURE** - Direct Excel monthly plan scheduling with work calendar integration, capacity optimization, and specialized monthly scheduling algorithms.

## Architecture & Technology Stack

### Frontend (Vue.js 3 Application)
- **Framework**: Vue.js 3.5.18 with TypeScript
- **UI Library**: Element Plus 2.8.8 (Chinese localization)
- **State Management**: Pinia 3.0.3
- **Build Tool**: Vite 7.0.6
- **Gantt Chart**: Vue Ganttastic 2.3.2 (@infectoone/vue-ganttastic)
- **Charts**: ECharts 6.0.0 (for general charting, not gantt charts)
- **Location**: `/frontend/`

### Backend (FastAPI Service)
- **Framework**: FastAPI 0.104.1 (async Python framework)
- **ORM**: SQLAlchemy 2.0.23 with async support
- **Database**: MySQL 8.0+ with aiomysql 0.2.0 driver
- **Cache**: Redis 7.0+ for session and data caching
- **Excel Processing**: openpyxl 3.1.2 for complex Excel parsing
- **Location**: `/backend/`

### Database Architecture
- **Primary**: MySQL 8.0+ (main data storage)
- **Cache**: Redis 7.0+ (caching and session management)
- **Schema**: Comprehensive table structure defined in `/scripts/database-schema.sql`
- **Monthly Planning Tables**: 
  - `aps_work_calendar` - Work day calendar and holiday management
  - `aps_monthly_plan` - Monthly production plan data
  - `aps_monthly_schedule_result` - Monthly scheduling results and work orders

## Development Commands

### Frontend Development
```bash
cd frontend/
npm install                    # Install dependencies
npm run dev                   # Development server (localhost:5173)
npm run build                 # Production build
npm run type-check           # TypeScript checking
npm run lint                  # ESLint with --fix
```

### Backend Development
```bash
cd backend/
pip install -r requirements.txt   # Install Python dependencies
python app/main.py                # Run FastAPI server (localhost:8000)

# Testing
pytest                            # Run test suite
pytest --cov=app                 # Run with coverage

# Code Quality
black .                          # Code formatting
isort .                          # Import sorting
flake8 .                         # Linting
```

## Core Business Logic

### Primary Data Flow
1. **Excel Upload** → File validation and storage (decade plans & monthly plans)
2. **Excel Parsing** → Complex Excel parsing with merged cells support
3. **Data Processing** → Apply business rules and validation
4. **Scheduling Algorithm** → ✅ **IMPLEMENTED** - Complete scheduling engine with pipeline management
5. **Work Order Generation** → Generate machine work orders
6. **MES Integration** → ✅ **IMPLEMENTED** - MES data export and integration services
7. **Monthly Plan Processing** → ✅ **NEW** - Direct monthly plan Excel processing with work calendar integration

### Critical Implementation Status
- ✅ **Fully Implemented**: Excel upload, parsing, data storage, query APIs (decade & monthly plans)
- ✅ **Core Algorithms**: Complete scheduling engine with merge, split, time correction, parallel processing algorithms
- ✅ **Monthly Scheduling**: Dedicated monthly plan algorithms with work calendar and capacity optimization
- ✅ **MES Integration**: Basic MES system interfaces and data export services
- ✅ **Gantt Visualization**: Gantt chart components and scheduling history views
- ✅ **Comprehensive Testing**: 21 test files covering algorithms, API endpoints, and integration scenarios

## Key File Structure & Patterns

### Backend Structure
```
backend/app/
├── api/v1/                    # ✅ API routes (RESTful design)
│   ├── data.py               # Data query endpoints
│   ├── plans.py              # Plan upload/parsing endpoints
│   ├── scheduling.py         # Scheduling execution endpoints
│   ├── work_orders.py        # Work order management
│   ├── machines.py           # Machine configuration
│   ├── mes.py                # MES system integration
│   ├── monthly_plans.py      # ✅ NEW - Monthly plan management endpoints
│   ├── work_calendar.py      # ✅ NEW - Work calendar management endpoints
│   └── router.py             # Route aggregation
├── core/config.py            # ✅ Configuration management
├── db/                       # ✅ Database layer
│   ├── connection.py         # Async MySQL/Redis connections
│   └── cache.py              # Redis cache utilities
├── models/                   # ✅ SQLAlchemy models
│   ├── base_models.py        # Machine, Material models
│   ├── decade_plan.py        # Plan data models
│   ├── scheduling_models.py  # Scheduling task models
│   ├── work_order_models.py  # Work order data models
│   ├── machine_config_models.py # Machine configuration models
│   ├── monthly_plan_models.py # ✅ NEW - Monthly plan data models
│   ├── work_calendar_models.py # ✅ NEW - Work calendar models
│   └── extended_models.py    # Extended business models
├── schemas/base.py           # ✅ Pydantic API schemas
├── services/                 # ✅ Business logic services
│   ├── excel_parser.py       # Complex Excel parsing logic
│   ├── database_query_service.py # Database query abstractions
│   ├── mes_integration.py    # MES system integration
│   ├── mes_data_export_service.py # MES data export
│   ├── work_order_sequence_service.py # Work order sequencing
│   ├── monthly_plan_parser.py # ✅ NEW - Monthly plan Excel parsing
│   └── work_calendar_service.py # ✅ NEW - Work calendar management
├── algorithms/               # ✅ Complete scheduling algorithms
│   ├── base.py              # Algorithm base classes and interfaces
│   ├── scheduling_engine.py  # Main scheduling pipeline manager
│   ├── merge_algorithm.py    # Rule-based plan merging
│   ├── split_algorithm.py    # Workload distribution logic
│   ├── time_correction.py    # Maintenance and shift handling
│   ├── parallel_processing.py # Synchronized machine operations
│   ├── work_order_generation.py # Work order creation
│   ├── pipeline.py           # Algorithm pipeline orchestration
│   └── monthly_scheduling/   # ✅ NEW - Monthly scheduling algorithms
│       ├── __init__.py      # Monthly scheduling module entry
│       ├── capacity_analyzer.py # Production capacity analysis
│       ├── work_calendar_processor.py # Work day processing
│       ├── plan_validator.py # Monthly plan validation
│       ├── resource_optimizer.py # Resource allocation optimization
│       ├── timeline_generator.py # Production timeline generation
│       ├── constraint_solver.py # Scheduling constraint solving
│       └── result_formatter.py # Scheduling result formatting
└── main.py                   # ✅ FastAPI application entry
```

### Frontend Structure
```
frontend/src/
├── components/               # ✅ Business components
│   ├── DecadePlanUpload.vue  # File upload with drag-drop
│   ├── DecadePlanTable.vue   # Data display tables
│   ├── ParseResult.vue       # Parse result visualization
│   ├── WorkOrderTable.vue    # Work order display
│   ├── GanttChartTab.vue     # Custom HTML/CSS gantt chart component
│   ├── MachineTable.vue      # Machine configuration
│   ├── MachineSpeedTable.vue # Machine speed settings
│   ├── ShiftConfigTable.vue  # Shift configuration
│   ├── MaintenancePlanTable.vue # Maintenance scheduling
│   ├── MonthlyPlanUpload.vue # ✅ NEW - Monthly plan file upload component
│   ├── MonthlyPlanTable.vue  # ✅ NEW - Monthly plan data display
│   ├── MonthlyGanttChart.vue # ✅ NEW - Monthly gantt chart visualization
│   ├── WorkCalendarTable.vue # ✅ NEW - Work calendar configuration
│   └── MonthlyScheduleResult.vue # ✅ NEW - Monthly scheduling result display
├── views/                    # ✅ Page components
│   ├── Home.vue              # Dashboard with statistics
│   ├── DecadePlanEntry.vue   # Plan entry workflow
│   ├── DecadePlanDetail.vue  # Plan details view
│   ├── SchedulingManagement.vue # Scheduling task management
│   ├── SchedulingHistory.vue # Historical scheduling data
│   ├── GanttChart.vue        # Vue Ganttastic-based gantt chart page
│   ├── MachineConfig.vue     # Machine configuration page
│   ├── MESMonitoring.vue     # MES system monitoring
│   ├── MonthlyPlanEntry.vue  # ✅ NEW - Monthly plan entry workflow
│   ├── MonthlyPlanDetail.vue # ✅ NEW - Monthly plan details view
│   ├── MonthlyScheduling.vue # ✅ NEW - Monthly scheduling management
│   └── WorkCalendarConfig.vue # ✅ NEW - Work calendar configuration page
├── services/api.ts           # ✅ API client with axios
├── stores/                   # ✅ State management
│   ├── decade-plan.ts        # Decade plan state management
│   └── monthly-plan.ts       # ✅ NEW - Monthly plan state management
├── router/index.ts           # ✅ Vue Router configuration
└── types/api.ts              # ✅ TypeScript definitions
```

## Development Guidelines

### Code Style & Standards
- **Backend**: Follow PEP 8, use `black` formatter, comprehensive docstrings in Chinese
- **Frontend**: ESLint configuration with Vue 3 + TypeScript rules
- **Database**: Consistent naming with `aps_` prefix, proper indexing

### Gantt Chart Implementation
- **Primary Tool**: Vue Ganttastic (@infectoone/vue-ganttastic) for professional timeline visualization
- **Usage**: Main gantt chart page (`views/GanttChart.vue`) uses Vue Ganttastic components
- **Custom Implementation**: `components/GanttChartTab.vue` uses custom HTML/CSS for simplified gantt display
- **ECharts**: Available for general charting needs but not used for gantt charts

### API Design Patterns
- **RESTful**: Consistent URL patterns `/api/v1/{resource}`
- **Response Format**: Standardized JSON with `code`, `message`, `data` structure
- **Error Handling**: Comprehensive exception handling with Chinese error messages
- **Validation**: Strict Pydantic models for request/response validation

### Business Rule Implementation
The system implements complex tobacco manufacturing business rules:
- **Merging Rules**: Combine plans with same month/product/machine
- **Splitting Rules**: Distribute workload across multiple machines
- **Time Correction**: Handle maintenance schedules and shift constraints
- **Parallel Processing**: Ensure synchronized machine operations
- **Monthly Plan Processing**: ✅ **NEW** - Work calendar integration, capacity optimization, and resource allocation
- **Work Day Management**: Holiday calendar, working day validation, and production time calculation

## Recent Achievements

### ✅ Completed Core Features
1. **Scheduling Algorithm Engine** - Complete implementation with:
   - Rule-based merging algorithms
   - Workload splitting and distribution  
   - Time correction for maintenance schedules
   - Parallel processing coordination
   - Work order generation pipeline

2. **Monthly Plan Scheduling** - ✅ **NEW FEATURE** - Full implementation with:
   - Excel monthly plan parsing and validation
   - Work calendar and holiday management
   - Production capacity analysis and optimization
   - Resource allocation with constraint solving
   - Timeline generation with work day validation
   - Monthly scheduling results with gantt visualization

3. **MES System Integration** - Functional implementation with:
   - MES data export services
   - Work order dispatch interfaces
   - Basic system monitoring capabilities

4. **Gantt Chart Visualization** - Full implementation with Vue Ganttastic:
   - Vue Ganttastic (v2.3.2) for professional timeline views
   - Custom HTML/CSS implementation in GanttChartTab component
   - Interactive work order timeline displays
   - Machine utilization and status visualization
   - Color-coded product categorization
   - Responsive design with custom styling
   - Monthly gantt chart component for monthly plan visualization

### 🔄 Areas for Enhancement (Medium Priority)
1. **Performance Optimization** - Fine-tuning of scheduling algorithms
2. **Advanced MES Features** - Real-time production status integration
3. **Enhanced Visualizations** - More detailed analytics dashboards
4. **Mobile Responsiveness** - Optimization for mobile devices

## Testing Strategy

### Backend Testing
- **Unit Tests**: pytest with async test support ✅ **IMPLEMENTED**
- **Integration Tests**: Database and API endpoint testing ✅ **IMPLEMENTED**
- **Algorithm Tests**: Comprehensive algorithm testing with boundary cases ✅ **IMPLEMENTED**
- **End-to-End Tests**: Complete pipeline testing ✅ **IMPLEMENTED**
- **Test Coverage**: Configured with coverage reporting (21 test files)
- **Test Data**: Fixtures in `/backend/tests/fixtures/`

### Frontend Testing
- **Framework**: Ready for Vue Test Utils setup
- **Type Checking**: TypeScript compilation as basic test
- **Linting**: ESLint for code quality

## Configuration Management

### Environment Variables
- Database connections via environment variables
- Redis configuration through settings
- File upload limits and allowed extensions
- Business rule parameters

### Configuration Files
- **Backend**: `/backend/app/core/config.py` - Pydantic Settings
- **Frontend**: Vite configuration with proxy to backend
- **Database**: Schema in `/scripts/database-schema.sql`

## Deployment Considerations

### Production Setup
- **Proxy Configuration**: Vite dev server proxies `/api` to `http://10.0.0.87:8000`
- **Database**: Requires MySQL 8.0+ with proper indexing
- **Dependencies**: Node.js 20.19.0+, Python 3.11+
- **CORS**: Currently allows all origins (should restrict in production)

## Business Context Notes

This system handles **烟草生产排产** (tobacco production scheduling) with specific Chinese business terminology and processes. The Excel parsing supports complex formats with merged cells representing machine assignments and time ranges. All user-facing text and error messages are in Chinese to match the business context.

**Monthly Plan Integration**: The system now supports direct Excel monthly plan processing with work calendar integration. Monthly plans include production targets, capacity constraints, and work day validations based on Chinese business calendar requirements.

**Important**: When implementing missing scheduling algorithms, ensure deep understanding of tobacco manufacturing constraints, machine capabilities, and regulatory requirements specific to Chinese tobacco industry standards. Monthly planning requires additional consideration of production capacity, work calendar constraints, and resource optimization.

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
