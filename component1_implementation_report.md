# 5 IMPLEMENTATION, INTEGRATION AND TESTING

This chapter describes the implementation, integration, verification, and deployment of Component 1: the log-ingestion and memory-failure detection pipeline. The component collects runtime telemetry and log messages from the monitored microservices, converts the raw data into structured events, detects memory and CPU failure signals, generates time-based windows, and exposes the results to the dashboard and downstream components.

## 5.1 Development environment and technology stack

### 5.1.1 Development environment

Component 1 was developed as a Python-based service and can be executed on Windows using the supplied `run_component1_ui.bat` launcher. The launcher creates or reuses a Python virtual environment, installs the dependencies in `requirements.txt`, starts the API, and opens the dashboard at `http://localhost:8001/`.

The main development requirements are:

| Area | Technology |
|---|---|
| Programming language | Python 3 |
| API framework | FastAPI |
| ASGI server | Uvicorn |
| Data processing | pandas and NumPy |
| Log-template mining | Drain3 |
| Text representation | scikit-learn TF-IDF |
| Similarity calculation | scikit-learn cosine similarity |
| Data visualisation | HTML, CSS, JavaScript, and Chart.js |
| Runtime communication | HTTP REST and WebSocket |
| Container/service access | Python `requests` client |
| Optional container support | Docker SDK for Python |
| Explainability and analysis support | SHAP |

The dependency versions and minimum versions are maintained in [`requirements.txt`](./requirements.txt). The persisted Drain3 model state is stored in [`models/drain3_state.bin`](./models/drain3_state.bin), while generated datasets and pipeline outputs are stored in the `output` directory.

### 5.1.2 Configuration

The main pipeline configuration is defined in `pipeline.py`. Important parameters include:

- Drain3 depth: `4`
- Drain3 similarity threshold: `0.4`
- Maximum Drain3 children: `100`
- Sliding-window size: `12` records
- Window duration: `5` minutes
- TF-IDF failure threshold: `0.12`
- Metric-fusion threshold: `3`
- Default live collection duration: `1` minute

Azure service endpoints are configured in [`services_config.json`](./services_config.json). In a production deployment, environment variables with the `AZURE_SERVICE_` prefix can be used instead of storing service URLs in the local configuration file.

## 5.2 Component implementation

### 5.2.1 System structure

Component 1 is implemented using two main Python modules and is deployed as an Azure Container App for operation:

- [`pipeline.py`](./pipeline.py) contains collection, preprocessing, parsing, classification, window generation, feature engineering, evaluation, and export logic.
- [`app.py`](./app.py) provides the FastAPI application, background worker, shared state, REST endpoints, and WebSocket endpoint.

The browser interface is implemented in [`ui/index.html`](./ui/index.html), [`ui/app.js`](./ui/app.js), and [`ui/styles.css`](./ui/styles.css). It displays current service status, raw telemetry, discovered log templates, detected failure windows, and summary statistics.

### 5.2.2 Processing pipeline

The pipeline is divided into the following stages:

#### Stage 1: Live log and metric collection

The collector reads the enabled service definitions and periodically sends `GET /metrics` requests to each configured Azure sidecar. For each response it records:

- Timestamp
- Service name
- Detected technology stack
- Log level and log message
- CPU percentage
- RAM percentage
- Heap memory used
- Garbage-collection count
- Initial ground-truth and failure-type fields

Each service is collected independently. The collector maintains service status, records HTTP failures, and handles services that do not expose an explicit garbage-collection counter. If a service provides metrics without a log message, the collector creates a descriptive message from the observed metric values so that the later log-classification stages can still operate.

Component 1 also supports CSV mode for repeatable processing of an existing dataset. The default input file is `data/raw_logs_metrics.csv`.

#### Stage 1.5: Preprocessing

The preprocessing stage prepares the collected records for analysis. It:

1. Removes duplicate records based on timestamp, service, and log message.
2. Forward-fills numeric values within each service.
3. Removes records with empty log messages.
4. Clips RAM and CPU values to the range 0–100 and heap values to the configured safe range.
5. Removes disallowed special characters from log messages.

This stage provides more consistent input for template mining and reduces the effect of malformed or incomplete telemetry.

#### Stage 2: Drain3 log parsing

Drain3 mines log templates from all messages using a stack-agnostic configuration. The stage adds:

- `log_template`: the parameterised log pattern
- `template_id`: the Drain3 cluster identifier

The Drain3 state is persisted to `models/drain3_state.bin`. The stage also reports the number of unique templates and the most frequent templates, which supports later analysis of service behaviour and failure patterns.

#### Stage 3: Three-layer hybrid classifier

The classifier combines complementary detection techniques:

1. **Keyword layer**: identifies explicit memory and CPU indicators such as `OUT OF MEMORY`, `MEMORY LEAK`, `GC OVERHEAD LIMIT`, `HEAP EXHAUSTED`, and `CPU SPIKE`.
2. **TF-IDF semantic layer**: compares mined templates with a failure-reference corpus using TF-IDF vectors and cosine similarity.
3. **Metric-fusion layer**: combines RAM, CPU, heap, and garbage-collection evidence. Higher scores are assigned when the configured resource thresholds are exceeded or when a service shows a garbage-collection spike.

The classifier produces the hybrid label, detection layer, failure type, and supporting scores. This combination allows the component to detect both explicit failure messages and failures represented primarily by resource behaviour.

#### Stage 4: Sliding-window analysis

The classified records are grouped into time-based windows. Window-level features include service and stack information, resource summaries, failure counts, classification evidence, and trend features. The implementation also supports memory-change features, incident-phase flags, RAM variability, and short-term failure trends.

Windows receive an incrementing `window_id`, which allows downstream consumers to request only records that have not already been processed.

#### Stage 5: Dataset export and evaluation

For CSV processing, the final windows are exported to the configured output directory. The generated files include the processed pipeline output and the machine-learning-ready dataset. Evaluation utilities calculate metrics such as precision, recall, F1 score, confusion matrices, per-service performance, ablation results, leave-one-service-out results, corpus-size experiments, window-size experiments, feature importance, and early-warning time.

### 5.2.3 API and state management

The FastAPI application starts the pipeline worker during application startup. A thread-safe shared state object stores the latest raw records, processed windows, active services, counters, and errors.

The main API surfaces are:

| Endpoint | Purpose |
|---|---|
| `GET /api/status` | Returns pipeline status, mode, uptime, row counts, active services, and the latest error |
| `GET /api/live-metrics` | Returns recent telemetry records |
| `GET /api/windows` | Returns the latest generated windows |
| `GET /api/templates` | Returns the most frequent mined templates and their failure association |
| `GET /api/stats` | Returns failure counts, layer contribution, F1 scores, and recent trends |
| `GET /api/component3/feed` | Supplies new enriched windows to Component 3 |
| `WS /ws/live` | Streams live metric updates to the dashboard |

The application converts pandas and NumPy values to JSON-compatible values before returning them from the API.

## 5.3 Integration with the other components

### 5.3.1 Integration with monitored microservices

Component 1 integrates with the monitored services through the `/metrics` HTTP contract. The configured services are Node.js, Python, Go, PHP, Ruby, and the authentication service. Each enabled service must return telemetry that can be mapped to CPU, memory, heap, garbage collection, log message, language, and request information.

The collector determines the application stack from the returned language value or, when necessary, from the service name. This allows the same processing pipeline to operate across multiple implementation technologies without requiring a separate classifier for every language.

### 5.3.2 Integration with the dashboard

The dashboard is served by the FastAPI application and uses the same origin as the API. On startup it:

1. Polls the status and data endpoints.
2. Opens the `/ws/live` WebSocket for live updates.
3. Renders pipeline stages, service filters, charts, templates, metrics, and failure windows.
4. Falls back to a local simulation when the backend is unavailable, allowing the interface to be inspected independently.

This integration makes the internal processing stages observable rather than exposing only the final classification result.

### 5.3.3 Integration with Component 3

Component 1 provides Component 3 with incremental processed windows through `GET /api/component3/feed`. The consumer supplies `since_window_id`, and Component 1 returns windows with larger identifiers together with:

- `last_window_id`
- `new_windows_count`
- The new window records
- `project_id`
- `label` and `hybrid_label` aliases
- Machine-learning features
- Five-minute and ten-minute trend fields where available

The feed uses the persisted pipeline output when available and falls back to the in-memory state. This permits Component 3 to continue consuming recent results while the live pipeline is running.

### 5.3.4 Integration with the Azure deployment

Component 1 is deployed as an application in **Azure Container Apps**. The deployed application runs the FastAPI/Uvicorn service and provides the dashboard, REST API, WebSocket stream, and Component 3 feed through the Azure application endpoint. The application also communicates over HTTPS with the monitored microservice Container Apps listed in [`services_config.json`](./services_config.json).

The Azure deployment therefore has two communication directions:

1. **Inbound communication:** users, the dashboard, and downstream components access Component 1 through the deployed Azure Container App endpoint.
2. **Outbound communication:** Component 1 periodically calls the `/metrics` endpoint of each enabled microservice Container App, collects the responses, and processes them through the detection pipeline.

The deployment configuration contains the enabled Node.js, Python, Go, PHP, Ruby, and authentication service endpoints. Environment-specific values and secrets should be supplied through Azure configuration or environment variables rather than committed to source control.

## 5.4 Verification and software testing

### 5.4.1 Verification approach

Verification covers static implementation checks, data-processing checks, API checks, integration checks, and user-interface checks.

The supplied [`_verify.py`](./_verify.py) script checks the presence of the live and CSV execution paths, the collector, dashboard state handling, stage boundaries, Docker dependency, thread-based collection, warning handling, output fields, and related implementation requirements.

The supplied [`test_trends.py`](./test_trends.py) script loads `output/ml_ready_dataset.csv`, runs the failure-trend feature generation, and reports summary statistics for:

- `trend_slope_5m`
- `trend_max_failures_5m`
- `trend_variance_5m`
- `trend_slope_10m`
- `trend_max_failures_10m`
- `trend_variance_10m`

### 5.4.2 Test levels

#### Unit and function-level testing

The preprocessing, Drain3 parsing, hybrid classification, trend generation, feature engineering, and export functions can be exercised independently with pandas DataFrames. Test data should include normal records, explicit memory-failure messages, CPU-spike messages, missing numeric values, duplicate rows, out-of-range values, and empty log messages.

#### Pipeline integration testing

An end-to-end test should execute the stages in order:

```text
collection/input -> preprocessing -> Drain3 -> hybrid classifier
-> sliding windows -> export/feed
```

The test should verify that each stage preserves the required identifying columns and that the final windows contain a `window_id`, service information, labels, detection-layer information, and feature columns.

#### API testing

The REST endpoints should be checked for:

- Successful JSON responses.
- Correct handling of `limit` and `since_window_id` parameters.
- Empty-state responses before data is available.
- Correct failure and normal counts.
- Correct serialization of timestamps and NumPy/pandas scalar values.
- Incremental feed behaviour when a previously returned `window_id` is supplied.

The WebSocket should be tested for connection establishment and receipt of `metrics_update` messages.

#### Integration testing

Integration tests should use a mock sidecar, such as [`mock_azure_sidecar.py`](./mock_azure_sidecar.py), to return deterministic `/metrics` responses. The test should verify that the collector:

- Contacts each enabled service.
- Maps the returned language to the correct stack.
- Handles valid responses and non-200 responses.
- Handles timeouts and unavailable services.
- Produces records that can pass through all later stages.

#### User-interface testing

The dashboard should be checked for:

- Successful connection to the API.
- Correct status and counter updates.
- Service filtering.
- Correct rendering of raw metrics, templates, and windows.
- WebSocket reconnection after disconnection.
- Usable fallback simulation when the API is offline.

### 5.4.3 Test execution

From the Component 1 directory, the verification scripts can be run with:

```powershell
.\venv311\Scripts\python.exe _verify.py
.\venv311\Scripts\python.exe test_trends.py
```

The API and dashboard can be started with:

```powershell
.\run_component1_ui.bat
```

The final report should record the execution date, Python version, dataset used, number of input records, number of generated windows, detected failure windows, and the observed precision, recall, and F1 values. These values should be copied from the actual test run rather than estimated.

## 5.5 Deployment and operation

### 5.5.1 Azure Container Apps deployment

The operational version of Component 1 is deployed to Azure Container Apps. Azure provides the hosting, public HTTPS ingress, service-to-service networking, and restart management required for continuous operation. The deployed container starts the FastAPI application using the `app:app` object and exposes port `8001`.

The Azure deployment includes:

- The Component 1 Python application and its dependencies from [`requirements.txt`](./requirements.txt).
- The FastAPI backend and Uvicorn application server.
- The web dashboard files in the `ui` directory.
- The Drain3 model state and pipeline output directories.
- Network access to the monitored microservice Container Apps.
- Environment variables such as `PIPELINE_MODE` and `PIPELINE_DURATION_MINUTES`.
- HTTPS access for the dashboard, REST endpoints, WebSocket stream, and Component 3 feed.

After deployment, the application can be checked through the following endpoint structure, using the Azure Container App URL assigned to Component 1:

| Endpoint | Purpose |
|---|---|
| `https://<component1-azure-url>/` | Component 1 dashboard |
| `https://<component1-azure-url>/api/status` | Deployment and pipeline health |
| `https://<component1-azure-url>/api/live-metrics` | Recent telemetry |
| `https://<component1-azure-url>/api/component3/feed` | Downstream Component 3 integration |
| `wss://<component1-azure-url>/ws/live` | Live dashboard updates |

The actual Azure Container App URL should be inserted in place of `<component1-azure-url>` in the final submitted report. The deployment should be validated by opening the dashboard, checking `/api/status`, confirming access to the configured monitored services, and verifying that new windows are available through `/api/component3/feed`.

### 5.5.2 Local deployment

For local deployment:

1. Open a terminal in the Component 1 directory.
2. Run `run_component1_ui.bat`.
3. Allow the launcher to create `venv311` or reuse the existing virtual environment.
4. Wait for Uvicorn to start on port `8001`.
5. Open `http://localhost:8001/`.

The API is started with Uvicorn using the `app:app` application object and listens on all interfaces. For development, reload mode is enabled by the launcher.

### 5.5.3 Azure production configuration

The Azure Container Apps production configuration should include:

- Python dependencies installed from `requirements.txt`.
- The source files, UI files, and required model/output directories included.
- Component 1's Azure Container App ingress enabled on port `8001`.
- Azure service URLs supplied through Container App environment variables or managed configuration.
- Network access to the monitored service `/metrics` endpoints.
- Persistent storage if Drain3 state and generated output files must survive restarts or replacement replicas.
- Azure Container Apps logs, health monitoring, and restart policies configured.
- WebSocket support enabled for the live dashboard stream.

The live duration can be controlled using `PIPELINE_DURATION_MINUTES`. The pipeline mode can be selected using `PIPELINE_MODE`, with `live` as the default and `csv` available for offline dataset processing.

### 5.5.4 Operational monitoring

Operators should monitor:

- Azure Container App revision and replica health.
- Azure ingress availability and HTTPS response status.
- API availability and response time.
- `GET /api/status` for worker status and the latest error.
- Number of active services and collected records.
- Number of generated windows and failure windows.
- Service HTTP errors, timeouts, and unavailable sidecars.
- Output-file growth and available disk space.
- Memory and CPU usage of the Component 1 process itself.

The `last_error` field in `/api/status`, service status messages, pipeline logs, and the generated output files should be used when diagnosing failures. A restart should be performed only after checking whether the problem is caused by an unavailable monitored service, invalid configuration, or a local processing error.

### 5.5.5 Limitations and maintenance

The current live API keeps the latest data in process memory, so a process restart clears the dashboard's in-memory state. Persisted CSV outputs provide recovery and audit support, but production deployments should use suitable persistent storage and log retention policies.

Configuration thresholds should be reviewed when the monitored services, traffic patterns, or failure definitions change. Any changes to the classifier thresholds, feature schema, or Component 3 feed contract should be tested together with the downstream consumer.
