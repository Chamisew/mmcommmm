# 6 RESULTS AND VALIDATION

This chapter presents the results obtained from Component 1, the technical outputs produced by the implementation, the validation performed by users or stakeholders, the results of integration with the other components, and the main findings. Component 1 is responsible for collecting telemetry and log messages from the monitored Azure microservices, mining log templates, detecting memory-failure conditions, generating sliding-window features, and exposing the results to the dashboard and downstream components.

The numerical results in this chapter are based on the generated output snapshot available in the `output` directory. The results are reported as an observational evaluation of the implemented detector. They must not be presented as supervised classification accuracy because the current live collection has `UNKNOWN` ground-truth labels. The final dissertation version should update the tables if a new experiment or labelled evaluation dataset is used.

## 6.1 Research results

### 6.1.1 Research objective

The research objective of Component 1 was to determine whether heterogeneous microservice logs and runtime metrics could be combined to identify memory-related failures in a technology-independent way. The component was designed to avoid dependence on a single programming language or fixed log format by combining:

- Drain3 log-template mining.
- Keyword-based detection.
- TF-IDF and semantic similarity.
- Runtime metric fusion using RAM, heap, and garbage-collection features.
- Sliding-window and trend-based feature generation.

### 6.1.2 Dataset processing results

The generated output snapshot contains the following records:

| Dataset or output | Records | Description |
|---|---:|---|
| `live_raw_collection.csv` | 55,503 | Raw telemetry and log records collected from the services |
| `pipeline_output.csv` | 54,128 | Records after preprocessing, parsing, classification, and window generation |
| `ml_ready_dataset.csv` | 54,095 | Feature-enriched dataset prepared for machine-learning analysis |

The difference between the raw and processed record counts is expected because preprocessing removes or transforms duplicate, invalid, or incomplete records before generating the final windows and features.

### 6.1.3 Service coverage

The raw collection includes the following services:

| Service | Raw records |
|---|---:|
| `php-azure` | 11,139 |
| `ruby-azure` | 11,135 |
| `go-azure` | 11,082 |
| `node-azure` | 11,075 |
| `python-azure` | 11,024 |
| `mock-auth-azure` | 48 |
| **Total** | **55,503** |

The results show that Component 1 can process telemetry from multiple technology stacks through a common schema. The small number of `mock-auth-azure` records should be considered when comparing services because it does not have the same observation volume as the other services.

### 6.1.4 Detection results

The processed pipeline output contains the following classification results:

| Result category | Count |
|---|---:|
| Windows classified as `FAILURE` | 46,293 |
| Windows classified as `NORMAL` | 7,835 |
| Total processed windows | 54,128 |
| Classified failure percentage | 85.52% |

The failure percentage is a descriptive result from this output snapshot. It should not be interpreted as model accuracy because the corresponding `ground_truth_label` values are `UNKNOWN`.

The detected failure types were:

| Failure type | Count |
|---|---:|
| `metric_only` | 44,188 |
| `memory_leak` | 189 |
| `none` | 9,601 |

The high number of `metric_only` results indicates that the metric-fusion layer contributed substantially to the classification output. This result is consistent with the design objective of detecting resource pressure even when a log message does not contain an explicit failure keyword.

### 6.1.5 Detection-layer contribution

The classification layers contributed as follows:

| Detection layer | Count |
|---|---:|
| `metric_fusion` | 44,188 |
| `normal` | 7,835 |
| `sentence_embedding_semantic` | 1,428 |
| `tfidf_semantic` | 338 |
| `keyword` | 176 |
| `keyword_metric_confirmed` | 163 |

These results demonstrate that the component does not rely on a single detection mechanism. Explicit keywords identify recognisable failure messages, semantic layers identify related log patterns, and metric fusion captures failures indicated by runtime behaviour.

### 6.1.6 Research validation requirements

The current output snapshot is suitable for demonstrating pipeline execution and detection-layer behaviour. However, a formal research accuracy claim requires a labelled validation dataset containing the expected class for each record or window. The final evaluation should report:

- Precision.
- Recall.
- F1 score.
- Confusion matrix.
- Per-service performance.
- Performance by failure type.
- False-positive and false-negative examples.
- Early-warning time before a confirmed incident.

The `ground_truth_label` column should contain `FAILURE` or `NORMAL` for the evaluation records before these metrics are interpreted as accuracy results.

### 6.1.7 Quantitative analysis of detector behaviour

The processed output provides evidence about how the detector behaves across services. The following table reports the observed detection rate, not accuracy:

| Service | Processed windows | Detected failures | Normal windows | Observed failure rate |
|---|---:|---:|---:|---:|
| `node-azure` | 22,500 | 21,765 | 735 | 96.73% |
| `python-azure` | 13,591 | 12,835 | 756 | 94.44% |
| `ruby-azure` | 11,889 | 7,938 | 3,951 | 66.77% |
| `php-azure` | 4,816 | 3,346 | 1,470 | 69.48% |
| `go-azure` | 1,284 | 397 | 887 | 30.92% |
| `mock-auth-azure` | 48 | 12 | 36 | 25.00% |

The variation between services is an important research finding. It may reflect genuine differences in workload and resource pressure, but it may also indicate service-specific threshold sensitivity or differences in telemetry quality. Consequently, aggregate detection rates should not replace per-service analysis.

The detector-layer distribution is:

| Detector layer | Windows | Percentage of processed output |
|---|---:|---:|
| Metric fusion | 44,188 | 81.64% |
| Normal classification | 7,835 | 14.47% |
| Sentence-embedding semantic | 1,428 | 2.64% |
| TF-IDF semantic | 338 | 0.62% |
| Keyword | 176 | 0.33% |
| Keyword plus metric confirmation | 163 | 0.30% |

The dominance of metric fusion indicates that the observed run was driven primarily by telemetry thresholds rather than explicit log keywords. This is useful evidence for the multimodal design, but it also identifies the metric-fusion layer as the highest-priority area for threshold calibration and false-positive analysis.

### 6.1.8 Feature and signal characteristics

Across the processed windows, the observed feature distributions were:

| Feature | Mean | Maximum |
|---|---:|---:|
| RAM percentage | 33.55 | 79.50 |
| Heap used (MB) | 945.80 | 1,433.80 |
| Window RAM mean | 33.54 | 67.00 |
| Window RAM maximum | 35.20 | 79.50 |
| Window heap maximum (MB) | 984.43 | 1,433.80 |
| GC spike count | 0.41 | 15 |

These descriptive statistics should be used to justify threshold selection and to identify possible class or service imbalance. They do not, by themselves, demonstrate that a threshold is optimal. Thresholds should be selected using a labelled development set and evaluated on a separate test set.

### 6.1.9 Advanced evaluation protocol

For a defensible fourth-year research evaluation, the data should be divided chronologically rather than randomly:

1. **Development period:** tune Drain3, TF-IDF, semantic, and metric thresholds.
2. **Validation period:** select the final configuration and operating threshold.
3. **Held-out test period:** report the final performance only once.

Records from the same incident should not be distributed across training and test periods because this can cause temporal leakage. The evaluation should include macro-averaged and micro-averaged precision, recall, and F1, together with 95% confidence intervals obtained by bootstrap resampling at the incident or window-group level.

Recommended comparison experiments are:

| Experiment | Purpose |
|---|---|
| Metric-only baseline | Measures the value of log evidence |
| Keyword-only baseline | Measures performance using explicit messages |
| TF-IDF-only baseline | Measures semantic template matching |
| Full hybrid detector | Measures the complete proposed method |
| Threshold sensitivity | Tests robustness to threshold changes |
| Leave-one-service-out evaluation | Tests cross-service generalisation |
| Time-based holdout | Tests performance on future observations |

The ablation results should be reported as changes in macro-F1, recall, false-positive rate, and detection latency. This provides stronger evidence than reporting a single aggregate score.

### 6.1.10 Error and failure-mode analysis

Each false positive and false negative in the labelled test set should be categorised. Suggested categories are:

- High resource usage without a confirmed incident.
- Normal workload incorrectly classified as failure.
- Failure message not represented in the reference corpus.
- Delayed or missing telemetry.
- Duplicate or incomplete records.
- Service-specific metric scale or threshold mismatch.
- Window boundary splitting an incident.

For each category, the report should include an example message, relevant metric values, predicted label, expected label, detection layer, and proposed mitigation. This analysis explains *why* the detector succeeds or fails and is more informative than a single accuracy value.

## 6.2 Product and technical results

### 6.2.1 Functional product results

Component 1 provides a working end-to-end product with the following capabilities:

1. Collecting telemetry from multiple Azure-hosted microservices.
2. Processing both live service data and CSV datasets.
3. Cleaning and normalising records before analysis.
4. Discovering log templates using Drain3.
5. Detecting explicit and semantic failure patterns.
6. Combining log evidence with resource metrics.
7. Producing sliding-window records and machine-learning features.
8. Displaying live results through a browser dashboard.
9. Providing REST and WebSocket access to processed results.
10. Supplying incremental windows to Component 3.

### 6.2.2 Technical output schema

The processed output contains fields for:

- Event and window identification.
- Timestamp, service, and technology stack.
- Mined log templates and template identifiers.
- RAM, heap, and garbage-collection metrics.
- Memory growth and heap-rate features.
- Window-level means, maxima, and standard deviations.
- Hybrid labels, ground-truth labels, label source, and failure type.
- Detection-layer information.

The machine-learning-ready output additionally contains project identifiers, incident-phase fields, five-minute and ten-minute memory-change features, and trend-related features.

### 6.2.3 API and dashboard results

The FastAPI service exposes status, metrics, windows, templates, statistics, and Component 3 feed endpoints. The dashboard consumes these endpoints through HTTP polling and the `/ws/live` WebSocket stream.

The technical implementation therefore provides both:

- A human-facing interface for monitoring and validation.
- A machine-facing interface for integration with downstream components.

The API also returns JSON-compatible representations of pandas timestamps and NumPy scalar values, allowing the dashboard and other services to consume the results without additional data conversion.

### 6.2.4 Performance and operational measurements

The final report should add measurements from the deployment environment for:

| Measurement | Result |
|---|---|
| Azure Container App region | `[Insert region]` |
| Container image or revision | `[Insert revision]` |
| Observation period | `[Insert start and end time]` |
| Average collection interval | `[Insert seconds]` |
| Average API response time | `[Insert milliseconds]` |
| Peak memory usage | `[Insert MB or percentage]` |
| Number of service timeouts | `[Insert count]` |
| Number of pipeline errors | `[Insert count]` |

These values should be collected from Azure monitoring and application logs rather than estimated from local execution.

### 6.2.5 Reproducibility and traceability

The reported results can be reproduced by preserving:

- The exact input CSV or live collection interval.
- The commit or source version used for the experiment.
- The values in `pipeline.CONFIG`.
- The contents of `services_config.json`, with secrets removed.
- The Python and dependency versions.
- The generated `pipeline_output.csv` and `ml_ready_dataset.csv`.
- The execution logs and Azure Container App revision.

The verification scripts [`_verify.py`](./_verify.py) and [`test_trends.py`](./test_trends.py) should be executed and archived with the final results. Each experiment should have a unique identifier and record its configuration, dataset, start time, end time, and output location.

## 6.3 User or stakeholder validation

### 6.3.1 Validation participants

Validation should be completed with the intended stakeholders, such as the project supervisor, system administrator, developer, or operational user. The final report should record the participant role without exposing unnecessary personal information.

| Participant role | Validation focus | Date | Result |
|---|---|---|---|
| `[Supervisor or researcher]` | Research outputs and interpretation | `[Date]` | `[Pass/changes requested]` |
| `[Developer]` | API, pipeline, and integration behaviour | `[Date]` | `[Pass/changes requested]` |
| `[Operational user]` | Dashboard usability and monitoring workflow | `[Date]` | `[Pass/changes requested]` |

### 6.3.2 Stakeholder validation activities

The following activities can be used to validate the implemented component:

1. Open the Component 1 dashboard using the deployed Azure URL.
2. Confirm that the service status changes from connecting to live.
3. Confirm that active services and collected-row counters are displayed.
4. Inspect recent RAM, heap, and garbage-collection values.
5. Review mined log templates and failure-related templates.
6. Check the failure-window count and detection-layer summary.
7. Filter the dashboard by service.
8. Confirm that live updates continue through the WebSocket connection.
9. Request the Component 3 feed and verify that new windows are returned.
10. Confirm that errors and unavailable services are visible through the status endpoint.

### 6.3.3 Acceptance criteria

| Acceptance criterion | Expected outcome | Evidence |
|---|---|---|
| Dashboard availability | Dashboard loads from the Azure Container App URL | Screenshot or URL test |
| Live collection | Records and active services increase during collection | `/api/status` response |
| Failure detection | Failure windows and detection layers are displayed | Dashboard/API output |
| Service filtering | User can inspect an individual service | Dashboard test |
| Downstream feed | Component 3 receives incremental windows | `/api/component3/feed` response |
| Error visibility | Collection or pipeline errors are exposed | `last_error` and logs |
| Reproducibility | CSV mode regenerates a consistent schema | Export comparison |

### 6.3.4 Validation feedback

The final submitted report should replace the following placeholders with actual feedback:

> Stakeholders confirmed that the dashboard provided a clear view of service health, collected telemetry, detected failure windows, and classification-layer contributions. The main improvement requests were `[insert feedback]`. These requests were addressed by `[insert implementation changes]`.

If stakeholder testing has not yet been completed, this statement should be changed to a planned-validation statement rather than presented as a completed result.

### 6.3.5 Usability and operational validation

Stakeholder validation should assess more than whether the dashboard loads. A short five-point questionnaire can measure:

| Dimension | Validation question |
|---|---|
| Interpretability | Can the user understand why a window was classified as a failure? |
| Timeliness | Does the dashboard provide information early enough for investigation? |
| Completeness | Are the required service and resource fields available? |
| Usability | Can the user locate an affected service and inspect its trend? |
| Trust | Does the user understand the difference between detection and confirmed ground truth? |

The report should present the number of participants, median score, score range, qualitative comments, and the changes made after feedback. If the sample is small, the result should be described as formative usability feedback rather than generalisable user research.

## 6.4 Integration results

### 6.4.1 Azure service integration

Component 1 successfully uses the configured Azure service endpoints as telemetry sources. The output snapshot confirms records from Node.js, Python, Go, PHP, Ruby, and authentication-related services. The common record schema allows these different stacks to be processed by the same collection and classification pipeline.

The deployed Component 1 application operates as an Azure Container App and provides the external application surface for the dashboard, API, WebSocket stream, and downstream feed. This verifies the intended separation between monitored services and the central detection component.

### 6.4.2 Component 3 feed integration

The integration with Component 3 is implemented through:

```text
GET /api/component3/feed?since_window_id=<last_processed_id>
```

The feed supports incremental consumption. Component 3 can provide its last processed window identifier, and Component 1 returns only windows with larger identifiers. The response contains the last available window identifier, the number of new windows, and the enriched window records.

The feed also standardises aliases and enrichment fields, including:

- `project_id`
- `label`
- `hybrid_label`
- Trend fields
- Machine-learning feature fields

This reduces coupling between the internal pipeline schema and the downstream component.

### 6.4.3 Dashboard integration

The dashboard integration was validated through the REST endpoints and WebSocket channel. The browser application retrieves:

- Current status.
- Live metrics.
- Mined templates.
- Generated windows.
- Statistical summaries.
- Component 3 feed data.

The dashboard can also reconnect to the WebSocket after a connection interruption and can display a fallback simulation when the backend is unavailable.

### 6.4.4 Integration test results

The final report should record the actual integration test outcomes:

| Integration test | Expected result | Actual result |
|---|---|---|
| Azure sidecar `/metrics` request | Valid telemetry is collected | `[Pass/Fail]` |
| Multiple technology stacks | Services are mapped to the common schema | `[Pass/Fail]` |
| Component 1 REST API | JSON data is returned from all required endpoints | `[Pass/Fail]` |
| Component 1 WebSocket | Live metric updates are received | `[Pass/Fail]` |
| Component 3 incremental feed | Only new windows are returned | `[Pass/Fail]` |
| Service failure handling | Timeout or HTTP errors are recorded | `[Pass/Fail]` |
| Azure deployment access | Public HTTPS endpoint is reachable | `[Pass/Fail]` |

### 6.4.5 Data-contract validation

Integration should also validate the data contract between Component 1 and Component 3. For every feed response, verify that:

- `last_window_id` is monotonic.
- `new_windows_count` equals the number of returned windows.
- Returned `window_id` values are greater than `since_window_id`.
- Required fields such as `service_name`, `timestamp`, `label`, and `project_id` are present.
- Repeating a request with the same `since_window_id` is deterministic for an unchanged output state.
- Missing optional trend fields do not prevent downstream processing.

These checks establish semantic compatibility, not only network connectivity.

## 6.5 Summary of findings

The results demonstrate that Component 1 provides a complete implementation for multi-service telemetry ingestion and memory-failure detection. The component processed 55,503 raw records and generated 54,128 classified windows in the available output snapshot. It covered six configured services and produced both a pipeline output dataset and a machine-learning-ready dataset.

The hybrid design produced evidence from multiple sources. Metric fusion was the most frequently used detection layer, while keyword and semantic layers provided additional detection mechanisms for explicit and semantically related failure messages. The results support the use of a combined log-and-metric approach rather than relying only on fixed keywords or only on resource thresholds.

From a product perspective, the component provides a live dashboard, REST API, WebSocket updates, persistent output files, and an incremental feed for Component 3. From an operational perspective, it is deployed through Azure Container Apps and can communicate with the monitored microservice deployments through their `/metrics` endpoints.

The main validation limitation is that the available output snapshot contains `UNKNOWN` ground-truth labels. Therefore, the reported failure counts describe system detections but do not establish classification accuracy. A labelled validation dataset and stakeholder acceptance evidence are required before final claims are made about precision, recall, F1 score, false-positive rate, or false-negative rate.

Overall, the implementation meets the functional integration objectives for Component 1 and provides a substantial experimental foundation. The remaining work for a complete research validation is to:

1. Add or verify labelled ground-truth data.
2. Run the formal evaluation scripts on the labelled dataset.
3. Record Azure performance and availability measurements.
4. Complete stakeholder validation and document the feedback.
5. Insert the final deployed Azure URL and integration test evidence.
