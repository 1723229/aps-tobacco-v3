# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

APS智慧排产系统 (APS Tobacco v3) - An intelligent production scheduling system specifically designed for tobacco manufacturing. This system implements advanced scheduling algorithms to process Excel-based production plans, optimize machine allocation, and generate work orders for both packing machines (卷包机) and feeding machines (喂丝机).

**Key Focus**: The system is primarily designed for processing tobacco packaging production plans with complex business rules including merging, splitting, time correction, and parallel processing algorithms.

## Architecture & Technology Stack

### Frontend (Vue.js 3 Application)
- **Framework**: Vue.js 3.5.18 with TypeScript
- **UI Library**: Element Plus 2.8.8 (Chinese localization)
- **State Management**: Pinia 3.0.3
- **Build Tool**: Vite 7.0.6
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
1. **Excel Upload** → File validation and storage
2. **Excel Parsing** → Complex Excel parsing with merged cells support
3. **Data Processing** → Apply business rules and validation
4. **Scheduling Algorithm** → ⚠️ **NOT IMPLEMENTED** - Core scheduling engine missing
5. **Work Order Generation** → Generate machine work orders
6. **MES Integration** → ⚠️ **NOT IMPLEMENTED** - External system integration missing

### Critical Implementation Status
- ✅ **Fully Implemented**: Excel upload, parsing, data storage, query APIs
- ❌ **Missing Core Logic**: All scheduling algorithms (`/backend/app/algorithms/` is empty)
- ❌ **Missing Integration**: MES system interfaces
- ❌ **Missing Visualization**: Gantt chart components

## Key File Structure & Patterns

### Backend Structure
```
backend/app/
├── api/v1/                    # ✅ API routes (RESTful design)
│   ├── data.py               # Data query endpoints
│   ├── plans.py              # Plan upload/parsing endpoints
│   └── router.py             # Route aggregation
├── core/config.py            # ✅ Configuration management
├── db/                       # ✅ Database layer
│   ├── connection.py         # Async MySQL/Redis connections
│   └── cache.py              # Redis cache utilities
├── models/                   # ✅ SQLAlchemy models
│   ├── base_models.py        # Machine, Material models
│   └── decade_plan.py        # Plan data models
├── schemas/base.py           # ✅ Pydantic API schemas
├── services/excel_parser.py  # ✅ Complex Excel parsing logic
├── algorithms/               # ❌ EMPTY - Core scheduling missing
└── main.py                   # ✅ FastAPI application entry
```

### Frontend Structure
```
frontend/src/
├── components/               # ✅ Business components
│   ├── DecadePlanUpload.vue  # File upload with drag-drop
│   ├── DecadePlanTable.vue   # Data display tables
│   └── ParseResult.vue       # Parse result visualization
├── views/                    # ✅ Page components
│   ├── Home.vue              # Dashboard with statistics
│   ├── DecadePlanEntry.vue   # Plan entry workflow
│   └── DecadePlanDetail.vue  # Plan details view
├── services/api.ts           # ✅ API client with axios
├── stores/decade-plan.ts     # ✅ Pinia state management
├── router/index.ts           # ✅ Vue Router configuration
└── types/api.ts              # ✅ TypeScript definitions
```

## Development Guidelines

### Code Style & Standards
- **Backend**: Follow PEP 8, use `black` formatter, comprehensive docstrings in Chinese
- **Frontend**: ESLint configuration with Vue 3 + TypeScript rules
- **Database**: Consistent naming with `aps_` prefix, proper indexing

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

## Critical Missing Components

### 1. Scheduling Algorithm Engine (High Priority)
**Location**: `/backend/app/algorithms/` (currently empty)
**Required**: Core scheduling algorithms for:
- Rule-based merging (`merge_algorithm.py`)
- Workload splitting (`split_algorithm.py`) 
- Time correction (`time_correction.py`)
- Parallel processing (`parallel_processing.py`)

### 2. MES System Integration (Medium Priority)
**Required**: External system interfaces for:
- Maintenance schedule synchronization
- Work order dispatch to MES
- Production status feedback

### 3. Gantt Chart Visualization (Medium Priority)
**Required**: Frontend visualization components for:
- Timeline view of work orders
- Machine utilization charts
- Schedule conflict visualization

## Testing Strategy

### Backend Testing
- **Unit Tests**: pytest with async test support
- **Integration Tests**: Database and API endpoint testing
- **Test Coverage**: Configured with coverage reporting
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

**Important**: When implementing missing scheduling algorithms, ensure deep understanding of tobacco manufacturing constraints, machine capabilities, and regulatory requirements specific to Chinese tobacco industry standards.