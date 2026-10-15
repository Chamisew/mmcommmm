# 1.6 Research questions or hypotheses

This research investigates whether a technology-independent monitoring component can detect memory failures in heterogeneous microservice systems by combining log information with runtime memory telemetry. The study focuses on memory-related conditions, including memory pressure, heap growth, memory leaks, garbage-collection abnormalities, and out-of-memory behaviour.

The proposed Component 1 collects memory telemetry and log messages from microservices implemented using different technology stacks. It then applies log-template mining, memory-related keyword detection, semantic matching, memory-metric fusion, and sliding-window feature generation. The research questions and hypotheses are therefore defined around detection effectiveness, cross-service generalisation, the contribution of the hybrid approach, early warning capability, and operational integration.

## 1.6.1 Main research question

**RQ1: To what extent can a technology-independent hybrid log-and-metric analysis component detect memory failures in heterogeneous microservice systems?**

This question evaluates whether the proposed approach can identify memory failures across multiple microservices without requiring a separate detector for each programming language or framework. The evaluation considers detection effectiveness, robustness across services, and the usefulness of combining log evidence with runtime memory metrics.

## 1.6.2 Specific research questions

### RQ1.1: Memory-failure detection effectiveness

**How accurately can Component 1 distinguish memory-failure windows from normal operating windows?**

This question will be evaluated using a labelled dataset and the following measures:

- Precision.
- Recall.
- F1 score.
- Specificity.
- False-positive rate.
- False-negative rate.
- Confusion matrix.

The evaluation will be performed at window level and, where possible, at incident level.

### RQ1.2: Contribution of the hybrid detection approach

**Does combining log-template information with runtime memory metrics improve memory-failure detection compared with using either source independently?**

The full hybrid detector will be compared with the following baselines:

1. Memory-metric-only detection.
2. Keyword-only detection.
3. Semantic log-template-only detection.
4. Full hybrid log-and-metric detection.

The comparison will focus on changes in precision, recall, F1 score, false-positive rate, and detection latency.

### RQ1.3: Contribution of individual detection layers

**Which detection layer contributes most effectively to identifying memory failures?**

The component contains the following main detection layers:

- Explicit memory-keyword detection.
- Semantic log-template detection.
- Memory metric-fusion detection.

An ablation study will remove or disable one layer at a time. The performance difference between the complete model and each ablated version will be used to estimate the contribution of that layer.

### RQ1.4: Cross-technology and cross-service generalisation

**Can the same detection approach identify memory failures across microservices implemented using different technology stacks?**

The research will evaluate services such as Node.js, Python, Go, PHP, Ruby, and authentication-related services using a common input schema. Performance will be reported:

- Across all services.
- Separately for each service.
- By technology stack.
- Using leave-one-service-out evaluation where sufficient labelled data is available.

This question examines whether the approach generalises beyond the service or log format used during development.

### RQ1.5: Value of log-template mining

**Does Drain3 log-template mining improve the consistency and usefulness of memory-related log analysis?**

This question evaluates whether converting variable log messages into structured templates:

- Reduces the effect of changing parameter values.
- Groups structurally similar memory messages.
- Improves semantic matching.
- Reduces the number of unique patterns requiring manual analysis.
- Improves downstream classification performance.

The comparison will use raw-message analysis and template-based analysis where feasible.

### RQ1.6: Early-warning capability

**Can Component 1 identify memory deterioration before an observable memory failure is confirmed?**

Early-warning capability will be measured by calculating the time between the first valid memory-failure prediction and the confirmed incident or ground-truth failure point. The evaluation will report:

- Mean early-warning time.
- Median early-warning time.
- Minimum and maximum early-warning time.
- Percentage of incidents detected before confirmation.
- Missed-incident rate.

An early warning will only be counted when it occurs before the confirmed failure and is not a duplicate prediction from the same incident.

### RQ1.7: Robustness to incomplete and noisy telemetry

**How robust is the component when memory telemetry or log messages are incomplete, delayed, duplicated, or noisy?**

Robustness will be evaluated using controlled data-quality scenarios, including:

- Missing RAM values.
- Missing heap values.
- Missing garbage-collection values.
- Empty log messages.
- Duplicate records.
- Out-of-range memory values.
- Delayed observations.
- Unavailable service endpoints.

The effect of each condition will be measured using detection performance, record retention, processing errors, and system availability.

### RQ1.8: Operational integration

**Can Component 1 operate reliably as an Azure Container App and provide usable results to the dashboard and downstream components?**

This question evaluates the technical operation of the deployed component, including:

- Availability of the Azure-hosted API.
- Successful collection from monitored Azure microservices.
- REST endpoint correctness.
- WebSocket live-update behaviour.
- Incremental delivery through the Component 3 feed.
- Recovery from service timeouts and temporary failures.
- Response time and resource usage.

## 1.6.3 Research hypotheses

The hypotheses are stated so that they can be tested using the evaluation methods described in the methodology and results chapters.

### H1: Hybrid detection effectiveness

**H1:** The full hybrid log-and-metric detector achieves a higher F1 score for memory-failure detection than at least one single-source baseline.

The null hypothesis is:

**H0-1:** The full hybrid detector does not achieve a higher F1 score than the single-source baselines.

The hypothesis will be tested using paired predictions on the same held-out test windows. Where appropriate, a bootstrap confidence interval or a paired statistical comparison will be used.

### H2: Log and metric complementarity

**H2:** Combining memory-related log evidence with runtime memory metrics improves recall without causing an unacceptable increase in the false-positive rate.

The null hypothesis is:

**H0-2:** Combining log evidence with memory metrics does not improve recall or produces an unacceptable false-positive increase.

The acceptable false-positive threshold must be defined before final evaluation. For example, the study may define an operational threshold based on stakeholder requirements.

### H3: Metric-fusion contribution

**H3:** The memory metric-fusion layer detects memory-failure windows that are not detected by explicit keyword matching alone.

The null hypothesis is:

**H0-3:** The memory metric-fusion layer does not identify additional valid memory-failure windows beyond keyword matching.

This hypothesis will be evaluated using labelled windows and by analysing the overlap between keyword-based and metric-fusion predictions.

### H4: Semantic-template contribution

**H4:** Template-based semantic matching detects a meaningful number of memory-related log patterns that do not contain the predefined memory keywords.

The null hypothesis is:

**H0-4:** Template-based semantic matching does not detect additional valid memory-related patterns beyond explicit keyword matching.

The analysis will compare the number and validity of semantic-only detections with keyword detections.

### H5: Cross-service generalisation

**H5:** The hybrid detector achieves acceptable and reasonably consistent memory-failure detection performance across the evaluated technology stacks.

The null hypothesis is:

**H0-5:** Detection performance varies substantially between technology stacks and does not generalise across services.

The definition of “acceptable” should be specified before testing. A suitable criterion may include a minimum per-service F1 score and a maximum allowed difference between the best and worst service, subject to the size and quality of each service dataset.

### H6: Early-warning capability

**H6:** The component identifies a significant proportion of confirmed memory incidents before the failure confirmation point.

The null hypothesis is:

**H0-6:** The component does not provide useful early warning before confirmed memory incidents.

This hypothesis requires timestamped ground-truth incident boundaries. Predictions generated after the confirmed incident must not be counted as early warnings.

### H7: Robustness to data-quality problems

**H7:** The preprocessing and hybrid detection pipeline maintains acceptable operation when a controlled proportion of memory telemetry or log messages is missing or noisy.

The null hypothesis is:

**H0-7:** Missing or noisy inputs cause unacceptable degradation or processing failure.

The experiment should define the corruption levels in advance, for example 5%, 10%, and 20% missing or corrupted observations.

### H8: Operational integration

**H8:** The Azure-deployed component can collect, process, expose, and transmit memory-failure results within the operational requirements of the wider system.

The null hypothesis is:

**H0-8:** The deployed component does not satisfy the required availability, response-time, data-contract, or downstream-integration requirements.

This hypothesis will be evaluated using Azure deployment tests, endpoint tests, WebSocket tests, Component 3 feed tests, and failure-recovery tests.

## 1.6.4 Variables and operationalisation

### Independent variables

The main independent variables are:

- Detection configuration.
- Presence or absence of log evidence.
- Presence or absence of memory-metric evidence.
- Detection layer enabled or disabled.
- Technology stack.
- Service identity.
- Data-quality condition.
- Sliding-window size.
- Similarity and metric thresholds.

### Dependent variables

The main dependent variables are:

- Predicted memory-failure label.
- Precision.
- Recall.
- F1 score.
- Specificity.
- False-positive rate.
- False-negative rate.
- Detection latency.
- Early-warning time.
- Number of valid memory-failure incidents detected.
- API response time.
- Feed delivery correctness.
- Service availability during collection.

### Control variables

Where possible, the following should remain consistent across comparative experiments:

- Input dataset.
- Ground-truth labels.
- Observation period.
- Window-generation method.
- Evaluation split.
- Preprocessing rules.
- Random seeds for reproducible experiments.
- Hardware and deployment configuration.

## 1.6.5 Hypothesis testing and decision rules

The evaluation should follow these rules:

1. Ground-truth labels must be created or verified before accuracy metrics are calculated.
2. Development and test data must be separated chronologically where the data represents a live system.
3. Records from the same incident must not be split across evaluation sets.
4. Thresholds must be selected using development or validation data, not the final test set.
5. Results must be reported for the complete detector and the defined baselines.
6. Per-service results must be reported rather than only an aggregate score.
7. Confidence intervals should be included for the main performance measures.
8. Missing or unknown labels must not be silently treated as normal or failure.
9. Any rejected hypothesis must be interpreted together with data quality, sample size, and service imbalance.

The main hypothesis will be supported only if the full hybrid detector demonstrates a measurable improvement over the selected baseline on the held-out test set and the improvement is practically meaningful for memory-failure monitoring.

## 1.6.6 Expected contribution

The expected research contribution is a reusable, technology-independent memory-failure detection component that combines structured log analysis with runtime memory behaviour. The study aims to demonstrate that:

- Memory failures can be detected across heterogeneous microservices using a common representation.
- Memory telemetry can identify failure patterns that are not explicitly recorded in logs.
- Log-template mining can reduce variability in messages and support semantic detection.
- Hybrid evidence can improve detection coverage over a single detection source.
- Sliding-window memory features can support early warning and downstream analysis.
- The approach can be integrated into an Azure-hosted monitoring architecture.

The conclusions will be based on the results of the labelled evaluation, ablation studies, cross-service analysis, early-warning analysis, robustness experiments, and operational integration tests. Until those experiments are completed, the statements above should be treated as research objectives and testable expectations rather than confirmed findings.

