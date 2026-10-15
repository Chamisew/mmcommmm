# 5 IMPLEMENTATION, INTEGRATION AND TESTING

This chapter describes the implementation, integration, testing, deployment, and operation of Component 1. The component is responsible for collecting logs and memory-related telemetry from microservice applications, identifying memory-failure patterns, generating time-window features, and providing processed results to the dashboard and downstream components.

Component 1 was designed as a technology-independent memory-failure detection component. It can process services implemented using different technology stacks, including Node.js, Python, Go, PHP, Ruby, and authentication services. The component combines log-template mining, memory-related keyword detection, semantic similarity, and memory-metric analysis to identify abnormal memory behaviour.

## 5.1 Development environment and technology stack

### 5.1.1 Development environment

Component 1 was developed as a Python-based web service. Development and local testing were performed in a Windows environment using an isolated Python virtual environment. The project includes a launcher, [`run_component1_ui.bat`](./run_component1_ui.bat), which creates or reuses a virtual environment, installs the required dependencies, starts the API, and opens the monitoring dashboard.

The component can operate in two modes:

1. **Live mode:** collects memory telemetry and log messages from the configured Azure microservices.
2. **CSV mode:** processes a previously collected dataset for repeatable experiments and offline testing.

The main source files are:

| File | Responsibility |
|---|---|
| [`pipeline.py`](./pipeline.py) | Collection, preprocessing, log parsing, memory classification, windowing, feature generation, evaluation, and export |
| [`app.py`](./app.py) | FastAPI application, background worker, shared state, REST APIs, and WebSocket communication |
| [`ui/index.html`](./ui/index.html) | Dashboard structure and user interface |
| [`ui/app.js`](./ui/app.js) | Dashboard data retrieval, WebSocket connection, charts, filters, and rendering |
| [`ui/styles.css`](./ui/styles.css) | Dashboard presentation and responsive styling |
| [`services_config.json`](./services_config.json) | Azure service endpoint configuration |
| [`_verify.py`](./_verify.py) | Static implementation verification |
| [`test_trends.py`](./test_trends.py) | Verification of memory trend feature generation |
| [`mock_azure_sidecar.py`](./mock_azure_sidecar.py) | Mock service used for integration testing |

### 5.1.2 Technology stack

| Layer | Technology | Use in Component 1 |
|---|---|---|
| Programming language | Python 3 | Core implementation |
| API framework | FastAPI | REST and WebSocket APIs |
| Application server | Uvicorn | Runs the FastAPI application |
| Data processing | pandas | DataFrame processing and feature generation |
| Numerical processing | NumPy | Numeric conversion and statistical operations |
| Log-template mining | Drain3 | Converts variable log messages into reusable templates |
| Text processing | scikit-learn TF-IDF | Represents and compares log templates |
| Similarity calculation | Cosine similarity | Measures similarity to memory-failure reference messages |
| HTTP communication | Python `requests` | Calls Azure service `/metrics` endpoints |
| Web interface | HTML, CSS, JavaScript | Monitoring dashboard |
| Charts | Chart.js | Visualises memory and failure trends |
| Container/service support | Docker SDK | Supports container-related integration |
| Deployment platform | Azure Container Apps | Hosts the operational Component 1 service |

The dependencies are defined in [`requirements.txt`](./requirements.txt). The main packages include Drain3, pandas, NumPy, scikit-learn, FastAPI, Uvicorn, Docker, SHAP, psutil, and sentence-transformers.

### 5.1.3 Configuration and project artefacts

The primary processing configuration is defined in `pipeline.py`. Important values include:

| Configuration item | Value or purpose |
|---|---|
| Drain3 depth | `4` |
| Drain3 similarity threshold | `0.4` |
| Drain3 maximum children | `100` |
| Sliding-window size | `12` records |
| Sliding-window duration | `5` minutes |
| TF-IDF threshold | `0.12` |
| Memory metric-fusion threshold | `3` |
| Default live collection duration | `1` minute |
| Live output file | `output/live_raw_collection.csv` |

The Drain3 state is persisted in [`models/drain3_state.bin`](./models/drain3_state.bin). Generated datasets and processed results are stored in the `output` directory. The input dataset for offline execution is [`data/raw_logs_metrics.csv`](./data/raw_logs_metrics.csv).

Production-specific Azure service URLs are configured through [`services_config.json`](./services_config.json) or environment variables with the `AZURE_SERVICE_` prefix. Environment variables are preferred for deployment-specific values.

## 5.2 Component implementation

### 5.2.1 Component architecture

Component 1 consists of the following logical layers:

```text
Azure microservice / CSV input
            |
            v
Memory telemetry and log collection
            |
            v
Preprocessing and data quality checks
            |
            v
Drain3 log-template mining
            |
            v
Hybrid memory-failure detector
            |
            v
Sliding-window feature generation
            |
            v
Export, dashboard API, WebSocket, and Component 3 feed
```

The pipeline state is shared between the processing worker and the FastAPI endpoints through a thread-safe state object. Locks are used when updating or reading the current records, counters, status, active services, and errors.

### 5.2.2 Stage 1: Memory telemetry and log collection

The live collector loads enabled services from the service configuration and calls each service's `/metrics` endpoint at a fixed interval. The collector records:

- Timestamp.
- Service name.
- Technology stack.
- Log level.
- Log message.
- RAM percentage.
- Heap memory used.
- Garbage-collection count.
- Initial ground-truth label.
- Failure type.

If the service provides memory metrics without a log message, the collector creates a descriptive message based on the observed memory condition. For example, high memory or heap usage can produce a memory-pressure or heap-exhaustion message. This ensures that the subsequent log-processing stages can operate even when a service exposes telemetry but does not provide a detailed log message.

The collector also tracks service availability, HTTP status failures, timeouts, and collection warnings. Each service is collected in an independent thread so that a slow or unavailable service does not prevent collection from the other services.

### 5.2.3 Stage 1.5: Preprocessing

The preprocessing stage improves the quality and consistency of the data before log parsing. It performs the following operations:

1. Removes duplicate records using timestamp, service name, and log message.
2. Forward-fills missing numeric memory values within each service.
3. Removes records with empty or missing log messages.
4. Clips out-of-range RAM and heap values.
5. Removes unsupported special characters from log messages.
6. Resets the DataFrame index after filtering.

This stage is important because inconsistent memory values, duplicate observations, and missing messages can create incorrect templates or unreliable memory-failure signals.

### 5.2.4 Stage 2: Drain3 log-template mining

Drain3 processes the cleaned log messages and converts similar messages into parameterised templates. For example, messages containing different numeric values can be grouped into the same structural template.

The stage adds:

- `log_template`: the normalised message pattern.
- `template_id`: the Drain3 cluster identifier.

The trained Drain3 state is saved to `models/drain3_state.bin`. Persisting the state supports repeatable processing and allows the component to retain the discovered template structure between processing runs.

### 5.2.5 Stage 3: Hybrid memory-failure detection

The detector combines three forms of memory evidence:

#### Keyword detection

The keyword layer identifies explicit memory indicators, including:

- `MEMORY LEAK`
- `MEMORY PRESSURE`
- `OUT OF MEMORY`
- `HEAP GROWING`
- `HEAP EXHAUSTION`
- `HEAP SPACE`
- `GC OVERHEAD LIMIT`
- `HEAP USED CRITICAL`
- `MEMORY THRESHOLD`
- `HEAP EXHAUSTED`
- `MEMORY LIMIT`
- `HEAP PRESSURE`

#### Semantic template detection

The semantic layer represents log templates using TF-IDF vectors and compares them with a reference corpus of memory-failure messages. Templates with sufficient similarity to the memory-failure corpus are classified as memory-related failures even when they do not contain an exact keyword.

#### Memory metric fusion

The metric-fusion layer analyses memory-related telemetry, including:

- RAM percentage.
- Heap memory used.
- Memory growth.
- Heap growth rate.
- Garbage-collection count.
- Garbage-collection spikes.

The detector assigns a memory-failure score when configured memory thresholds are exceeded or when multiple memory indicators occur together. This allows the component to identify memory pressure that is not explicitly described in the log message.

The detector produces:

- `hybrid_label`
- `detection_layer`
- `failure_type`
- Memory-related scores
- Supporting window features

### 5.2.6 Stage 4: Sliding-window feature generation

The classified records are grouped into time-based windows. Window-level features include:

- Mean and maximum RAM usage.
- RAM standard deviation.
- Mean and maximum heap usage.
- Heap growth rate.
- Memory change over five minutes.
- Memory change over ten minutes.
- Garbage-collection spike count.
- Number of failure-related records.
- Detection-layer contribution.
- Service and technology stack.

Each window receives a monotonically increasing `window_id`. This identifier supports incremental downstream consumption and prevents Component 3 from repeatedly processing the same result.

### 5.2.7 Stage 5: Export and machine-learning preparation

The final stage exports processed records and creates a machine-learning-ready dataset. The generated output can contain:

- Processed pipeline windows.
- Memory-growth features.
- Incident-phase fields.
- Labels and failure types.
- Project identifiers.
- Trend features.

Evaluation utilities in `pipeline.py` support metric calculation, ablation studies, leave-one-service-out evaluation, corpus-size experiments, window-size experiments, feature importance, and early-warning analysis.

### 5.2.8 FastAPI application and API implementation

The FastAPI application starts a background pipeline worker during application startup. It exposes the following interfaces:

| Interface | Function |
|---|---|
| `GET /api/status` | Returns pipeline status, mode, uptime, record counts, active services, and errors |
| `GET /api/live-metrics` | Returns recent memory telemetry and classification fields |
| `GET /api/windows` | Returns the latest generated memory windows |
| `GET /api/templates` | Returns mined templates and memory-failure associations |
| `GET /api/stats` | Returns failure counts, normal counts, detector-layer counts, and trends |
| `GET /api/component3/feed` | Provides incremental enriched windows to Component 3 |
| `WS /ws/live` | Streams live metric updates to the dashboard |

The application sanitises pandas timestamps, NumPy numeric values, and missing values before returning JSON responses.

### 5.2.9 Dashboard implementation

The dashboard displays:

- Pipeline status.
- Total collected records.
- Active services.
- Number of mined templates.
- Number of detected memory-failure windows.
- Total generated windows.
- Failure percentage.
- Memory trends.
- Service-specific views.
- Detected templates and detection layers.

The browser application polls the REST endpoints and connects to `/ws/live` for real-time updates. It also contains a fallback simulation for interface testing when the backend is unavailable.

## 5.3 Integration with the other components

### 5.3.1 Integration with monitored Azure microservices

Component 1 integrates with the monitored microservices through the `/metrics` HTTP contract. Each service should expose memory telemetry in a compatible response format. The expected information includes:

- Memory percentage.
- Heap memory used.
- Garbage-collection count or related memory information.
- Log message.
- Log level.
- Programming language or stack.
- Request or service metadata where available.

The service configuration contains the enabled Azure endpoints for the Node.js, Python, Go, PHP, Ruby, and authentication services. Component 1 maps the returned language or service name to a common stack label and stores the telemetry in a common schema.

### 5.3.2 Integration with the Azure deployment

Component 1 itself is deployed as an Azure Container App. The deployed application hosts the FastAPI service and provides:

- The Component 1 dashboard.
- REST endpoints.
- WebSocket live updates.
- The Component 3 integration feed.

The deployment has two communication directions:

1. **Inbound:** users and downstream components access the deployed Component 1 URL over HTTPS.
2. **Outbound:** Component 1 calls the `/metrics` endpoints of the monitored microservice Container Apps.

Azure Container Apps provides the operational hosting environment, ingress, revision management, replica management, logging, and restart handling for Component 1.

### 5.3.3 Integration with the dashboard

The dashboard uses the same application origin as the FastAPI backend. It retrieves data using REST calls and receives live updates through the WebSocket connection.

The dashboard integration is complete when:

- The page loads from the Azure URL.
- `/api/status` reports a valid application state.
- Recent memory records are displayed.
- The service filter lists active services.
- Mined templates are displayed.
- Memory-failure windows are displayed.
- Live updates are received.
- Reconnection occurs after a temporary WebSocket failure.

### 5.3.4 Integration with Component 3

Component 1 supplies Component 3 through:

```text
GET /api/component3/feed?since_window_id=<last_processed_window_id>
```

The feed returns:

- `last_window_id`
- `new_windows_count`
- New processed windows
- `project_id`
- `label`
- `hybrid_label`
- Memory-growth features
- Five-minute and ten-minute trend fields where available

The incremental design allows Component 3 to request only windows generated after its last successfully processed window. This reduces duplicate processing and provides a clear integration contract.

### 5.3.5 Integration data-contract requirements

The integration contract should satisfy the following rules:

1. Returned `window_id` values must be greater than `since_window_id`.
2. `new_windows_count` must equal the number of returned windows.
3. `last_window_id` must be monotonic.
4. Required fields must be present in each window.
5. Optional trend fields must not prevent processing if unavailable.
6. Labels must use a consistent representation.
7. Timestamps must be serialisable and interpretable by the consumer.

## 5.4 Verification and software testing

### 5.4.1 Testing strategy

Testing was designed as a layered process:

1. Static implementation verification.
2. Unit testing of memory-processing functions.
3. Data-quality and schema testing.
4. End-to-end pipeline testing.
5. API testing.
6. WebSocket testing.
7. Azure sidecar integration testing.
8. Component 3 feed testing.
9. Dashboard usability testing.
10. Deployment smoke testing.

The goal is to verify not only that the service starts, but also that memory telemetry is transformed correctly and remains compatible with downstream components.

### 5.4.2 Test case summary

| Test ID | Test area | Expected result |
|---|---|---|
| TC-01 | Environment setup | Virtual environment and dependencies are available |
| TC-02 | Static verification | Required memory-pipeline features are present |
| TC-03 | Input loading | CSV input loads with the required schema |
| TC-04 | Duplicate removal | Duplicate records are removed correctly |
| TC-05 | Missing-memory handling | Missing memory values are handled per service |
| TC-06 | Outlier handling | Invalid memory values are clipped or rejected |
| TC-07 | Drain3 parsing | Memory log templates and template IDs are generated |
| TC-08 | Keyword detection | Explicit memory messages are detected |
| TC-09 | Semantic detection | Similar memory messages are detected |
| TC-10 | Metric fusion | Memory pressure from telemetry is detected |
| TC-11 | Sliding windows | Memory features and window IDs are generated |
| TC-12 | Output schema | Exported files contain required fields |
| TC-13 | API status | Status endpoint returns valid state |
| TC-14 | API memory metrics | Recent memory records are returned |
| TC-15 | API statistics | Memory-failure statistics are consistent |
| TC-16 | WebSocket updates | Live memory updates are received |
| TC-17 | Sidecar integration | Azure `/metrics` data is collected |
| TC-18 | Failure handling | Timeout and HTTP errors are recorded |
| TC-19 | Component 3 feed | Incremental windows are returned correctly |
| TC-20 | Azure smoke test | Deployed application is reachable and operational |

### 5.4.3 Detailed test cases

#### TC-01: Environment setup

| Item | Description |
|---|---|
| Objective | Confirm that the component can be prepared for execution |
| Input | Project directory and `requirements.txt` |
| Procedure | Run `run_component1_ui.bat` or create the virtual environment manually |
| Expected result | Python environment is available and dependencies can be imported |
| Evidence | Installation output and successful API startup |

#### TC-02: Static implementation verification

| Item | Description |
|---|---|
| Objective | Verify that required pipeline and live-collection features exist |
| Input | `pipeline.py`, `requirements.txt`, and `app.py` |
| Procedure | Run `_verify.py` |
| Expected result | All required verification checks pass |
| Evidence | `_verify.py` console output |

#### TC-03: Input schema validation

| Item | Description |
|---|---|
| Objective | Confirm that the input dataset contains the required memory fields |
| Input | `data/raw_logs_metrics.csv` |
| Procedure | Load the CSV and check timestamp, service, log message, RAM, heap, and garbage-collection columns |
| Expected result | Required fields exist and numeric memory fields can be converted |
| Evidence | Schema report and row count |

#### TC-04: Duplicate-record removal

| Item | Description |
|---|---|
| Objective | Confirm that repeated observations do not create duplicate pipeline events |
| Input | Dataset containing identical timestamp, service, and log-message records |
| Procedure | Run Stage 1.5 preprocessing |
| Expected result | Only the first record in each duplicate group remains |
| Evidence | Before-and-after row counts |

#### TC-05: Missing-memory handling

| Item | Description |
|---|---|
| Objective | Confirm that missing memory values are handled safely |
| Input | Records with missing RAM or heap values for one service |
| Procedure | Run preprocessing and inspect the resulting service records |
| Expected result | Values are forward-filled where possible; unresolved invalid records do not silently produce misleading results |
| Evidence | Null-count report before and after preprocessing |

#### TC-06: Memory outlier handling

| Item | Description |
|---|---|
| Objective | Confirm that invalid memory values do not distort classification |
| Input | RAM values below 0 or above 100 and invalid heap values |
| Procedure | Run preprocessing |
| Expected result | Values are clipped to the configured valid range or rejected according to the implementation |
| Evidence | Outlier count and corrected values |

#### TC-07: Drain3 memory-template parsing

| Item | Description |
|---|---|
| Objective | Verify that structurally similar memory messages produce common templates |
| Input | Messages such as heap-pressure and allocation-failure messages with different numeric values |
| Procedure | Run Stage 2 |
| Expected result | `log_template` and `template_id` are added and similar messages are grouped |
| Evidence | Template count and sample template output |

#### TC-08: Explicit memory-keyword detection

| Item | Description |
|---|---|
| Objective | Verify detection of explicit memory-failure messages |
| Input | `OutOfMemoryError`, `memory leak`, `heap exhausted`, and `GC overhead limit` messages |
| Procedure | Run Stage 3 |
| Expected result | Records are classified as memory failures through the keyword layer |
| Evidence | `hybrid_label`, `failure_type`, and `detection_layer` fields |

#### TC-09: Semantic memory detection

| Item | Description |
|---|---|
| Objective | Verify detection when the message is semantically related but does not exactly match a keyword |
| Input | Messages such as `allocation capacity is increasing rapidly` or `retained objects continue to grow` |
| Procedure | Run the TF-IDF or semantic template layer |
| Expected result | Sufficiently similar messages are classified as memory-related failures |
| Evidence | Similarity score, template, and detection layer |

#### TC-10: Memory metric-fusion detection

| Item | Description |
|---|---|
| Objective | Verify detection based on memory telemetry |
| Input | Records with increasing RAM, increasing heap, and garbage-collection spikes |
| Procedure | Run Stage 3 with log messages that do not explicitly state a failure |
| Expected result | The metric-fusion layer identifies memory pressure when the configured score is reached |
| Evidence | Memory metrics, score, label, and detection layer |

#### TC-11: Sliding-window feature generation

| Item | Description |
|---|---|
| Objective | Verify that memory trends are calculated over time windows |
| Input | Ordered records from one or more services |
| Procedure | Run Stage 4 |
| Expected result | Window IDs and memory features such as RAM mean, heap maximum, memory change, and GC spike count are generated |
| Evidence | Window output and feature-column checks |

#### TC-12: Output-schema validation

| Item | Description |
|---|---|
| Objective | Confirm that output files are suitable for analysis and integration |
| Input | Generated pipeline and ML-ready CSV files |
| Procedure | Check required column names, data types, and missing-value counts |
| Expected result | Required identifiers, memory features, labels, and timestamps are available |
| Evidence | Automated schema validation report |

#### TC-13: API status testing

| Item | Description |
|---|---|
| Objective | Verify application health reporting |
| Input | Running FastAPI application |
| Procedure | Request `GET /api/status` |
| Expected result | A JSON response contains status, mode, uptime, row counts, active services, and error information |
| Evidence | HTTP response and status payload |

#### TC-14: Live-memory API testing

| Item | Description |
|---|---|
| Objective | Verify that recent memory telemetry can be consumed by the dashboard |
| Input | Running pipeline with collected records |
| Procedure | Request `GET /api/live-metrics?limit=50` |
| Expected result | The response contains recent timestamped memory records and classification fields |
| Evidence | HTTP response, response schema, and sample records |

#### TC-15: Statistics API testing

| Item | Description |
|---|---|
| Objective | Verify consistency of memory-failure summary statistics |
| Input | Generated windows |
| Procedure | Request `GET /api/stats` and compare totals with the window dataset |
| Expected result | Failure windows, normal windows, percentages, detector-layer counts, and trends are consistent |
| Evidence | API-to-file comparison |

#### TC-16: WebSocket live-update testing

| Item | Description |
|---|---|
| Objective | Verify real-time delivery to the dashboard |
| Input | Running application and WebSocket client |
| Procedure | Connect to `/ws/live` and wait for `metrics_update` messages |
| Expected result | Valid JSON updates containing memory telemetry are received |
| Evidence | WebSocket connection log and received message |

#### TC-17: Azure sidecar integration testing

| Item | Description |
|---|---|
| Objective | Verify integration with monitored service deployments |
| Input | Azure `/metrics` endpoints or `mock_azure_sidecar.py` |
| Procedure | Start collection and inspect records from each enabled service |
| Expected result | Service records are collected, stack names are mapped, and memory fields are populated |
| Evidence | Service-level row counts and collector log |

#### TC-18: Service failure-handling testing

| Item | Description |
|---|---|
| Objective | Verify safe handling of unavailable services |
| Input | Timeout, invalid URL, and non-200 `/metrics` response |
| Procedure | Run the collector while one service is unavailable |
| Expected result | The service is marked unavailable, a warning is recorded, and other services continue to be processed |
| Evidence | Warning log, service status, and records from healthy services |

#### TC-19: Component 3 feed testing

| Item | Description |
|---|---|
| Objective | Verify incremental downstream integration |
| Input | `since_window_id` and generated windows |
| Procedure | Request `GET /api/component3/feed?since_window_id=0`, then repeat using the returned last window ID |
| Expected result | The first request returns new windows; the second request does not repeat already consumed windows |
| Evidence | Feed payload, window IDs, and count comparison |

#### TC-20: Azure deployment smoke testing

| Item | Description |
|---|---|
| Objective | Verify the operational deployment |
| Input | Azure Container App URL |
| Procedure | Open the dashboard and request `/api/status`, `/api/live-metrics`, and `/api/component3/feed` |
| Expected result | HTTPS endpoints respond, the dashboard loads, memory records appear, and the feed is accessible |
| Evidence | Azure URL, screenshots, HTTP responses, revision name, and application logs |

### 5.4.4 Test execution commands

From the Component 1 directory, the local verification scripts can be executed using:

```powershell
.\venv311\Scripts\python.exe _verify.py
.\venv311\Scripts\python.exe test_trends.py
```

The local API and dashboard can be started using:

```powershell
.\run_component1_ui.bat
```

For API smoke testing, the following endpoints should be checked:

```text
http://localhost:8001/api/status
http://localhost:8001/api/live-metrics
http://localhost:8001/api/windows
http://localhost:8001/api/templates
http://localhost:8001/api/stats
http://localhost:8001/api/component3/feed
```

In the final report, each test should be marked `Pass`, `Fail`, or `Blocked`, together with the execution date and evidence location.

### 5.4.5 Research-quality validation

The test cases above verify implementation and integration behaviour. They do not replace a labelled research evaluation. For research validation, the dataset should include confirmed memory-failure and normal labels. The final evaluation should use:

- Chronological development, validation, and test sets.
- Incident-level separation to avoid temporal leakage.
- Precision, recall, F1 score, and confusion matrix.
- Macro and micro averages.
- Per-service results.
- Per-failure-type results.
- False-positive and false-negative analysis.
- Detection latency or early-warning time.
- Confidence intervals where appropriate.

## 5.5 Deployment and operation

### 5.5.1 Azure Container Apps deployment

Component 1 is deployed as an Azure Container App for operational use. The deployed application runs the FastAPI/Uvicorn service and exposes the dashboard, REST API, WebSocket stream, and Component 3 feed through an HTTPS endpoint.

The Azure deployment contains:

- Component 1 source code.
- Python dependencies from `requirements.txt`.
- FastAPI and Uvicorn.
- Dashboard files in the `ui` directory.
- Drain3 model state.
- Required output directories.
- Azure service configuration.
- Environment variables for runtime operation.

The application should expose port `8001` through Azure Container Apps ingress. The final report should include the actual deployed URL:

```text
Component 1 Azure URL: [Insert deployed Azure Container App URL]
```

The main production endpoints are:

| Endpoint | Purpose |
|---|---|
| `https://<component1-url>/` | Dashboard |
| `https://<component1-url>/api/status` | Health and pipeline status |
| `https://<component1-url>/api/live-metrics` | Recent memory telemetry |
| `https://<component1-url>/api/windows` | Generated memory windows |
| `https://<component1-url>/api/component3/feed` | Downstream feed |
| `wss://<component1-url>/ws/live` | Live dashboard updates |

### 5.5.2 Azure runtime configuration

The following configuration should be supplied through Azure Container App environment variables or managed configuration:

| Variable | Purpose |
|---|---|
| `PIPELINE_MODE` | Selects `live` or `csv` processing mode |
| `PIPELINE_DURATION_MINUTES` | Controls live collection duration |
| `AZURE_SERVICE_NODE` | Node.js service endpoint where used |
| `AZURE_SERVICE_PYTHON` | Python service endpoint where used |
| `AZURE_SERVICE_GO` | Go service endpoint where used |
| `AZURE_SERVICE_PHP` | PHP service endpoint where used |
| `AZURE_SERVICE_RUBY` | Ruby service endpoint where used |
| `AZURE_SERVICE_AUTH` | Authentication service endpoint where used |

Environment-specific URLs and secrets should not be hard-coded into the source code. Azure configuration should be used instead.

### 5.5.3 Local development deployment

Local execution is used for development, debugging, and repeatable offline testing:

1. Open a terminal in the Component 1 directory.
2. Run `run_component1_ui.bat`.
3. Allow the script to create or reuse `venv311`.
4. Wait for Uvicorn to start on port `8001`.
5. Open `http://localhost:8001/`.

The local launcher starts Uvicorn in reload mode. This mode is suitable for development but should not be used as the production deployment strategy.

### 5.5.4 Operational monitoring

The following operational indicators should be monitored:

- Azure Container App revision status.
- Active replica status.
- HTTPS ingress availability.
- API response time.
- Pipeline status from `/api/status`.
- Number of collected records.
- Number of generated windows.
- Number of detected memory-failure windows.
- Active monitored services.
- Service timeouts and non-200 responses.
- Latest pipeline error.
- Container memory usage.
- Output-file growth and storage availability.

Component 1's research output remains focused on memory failures.

### 5.5.5 Failure recovery

When an issue occurs, operators should:

1. Check the Azure Container App revision and replica state.
2. Request `/api/status`.
3. Inspect the `last_error` field.
4. Check Azure application logs.
5. Confirm that monitored service `/metrics` endpoints are reachable.
6. Check configuration and environment variables.
7. Restart or redeploy only after identifying the likely cause.

If a monitored service is unavailable, Component 1 should continue processing available services and record the unavailable service as a warning. If the Component 1 application restarts, in-memory dashboard state is cleared, so persisted output files and persistent storage should be used when historical continuity is required.

### 5.5.6 Deployment acceptance checklist

| Checklist item | Status |
|---|---|
| Azure Container App deployed | `[Pass/Fail]` |
| HTTPS ingress enabled | `[Pass/Fail]` |
| Port `8001` configured | `[Pass/Fail]` |
| Dashboard accessible | `[Pass/Fail]` |
| `/api/status` responds | `[Pass/Fail]` |
| Azure memory telemetry collected | `[Pass/Fail]` |
| Drain3 state available | `[Pass/Fail]` |
| Memory-failure windows generated | `[Pass/Fail]` |
| WebSocket updates received | `[Pass/Fail]` |
| Component 3 feed accessible | `[Pass/Fail]` |
| Azure logs available | `[Pass/Fail]` |
| Restart and recovery verified | `[Pass/Fail]` |

### 5.5.7 Limitations

The current live application keeps the latest records in process memory. A restart therefore clears the in-memory dashboard state. Persisted CSV outputs and Drain3 state provide partial continuity, but production operation should use appropriate persistent storage and log-retention policies if complete historical recovery is required.

The output snapshot also contains `UNKNOWN` ground-truth labels for live records. Consequently, deployment and integration tests can confirm system operation, but formal memory-classification accuracy must be established using a separately labelled evaluation dataset.
