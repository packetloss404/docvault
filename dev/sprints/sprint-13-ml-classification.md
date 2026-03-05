# Sprint 13: ML Classification Pipeline

## Phase: 5 - Intelligence & AI
## Duration: 2 weeks
## Prerequisites: Sprint 12 (Retention, Quotas & Notifications)

---

## Sprint Goal
Build the ML-powered document classification system from Paperless-ngx: four separate classifiers for tags, correspondent, document type, and storage path using scikit-learn. Integrate into the processing pipeline with smart retraining and Redis-backed caching.

---

## Context for Agents

### Read Before Starting
- `/doc/product-spec.md` - Section 2.9 (ML/AI Module)
- `/doc/research/paperless-ngx-analysis.md` - Section 4 (ML Classification Pipeline) - direct port
- This is a direct adoption of Paperless-ngx's proven classification approach

---

## Tasks

### Task 13.1: DocumentClassifier Class
- Create `ml/` app
- DocumentClassifier class with four sub-classifiers:
  - tags_classifier (multi-label, MultiLabelBinarizer + MLPClassifier)
  - correspondent_classifier (single-label)
  - document_type_classifier (single-label)
  - storage_path_classifier (single-label)
- Feature extraction: CountVectorizer with 1-2 ngrams, 1% min_df
- Content preprocessing: regex tokenization, case normalization, Snowball stemming, stop word filtering
- Redis-backed LRU cache for stemming (10,000 element capacity)
- Large document handling: crop to 1.2M chars (800k start + 200k end)

### Task 13.2: Training Pipeline
- Train only on documents with MATCH_AUTO algorithm
- Hash-based change detection (track hash of AUTO-matched document IDs)
- Skip retraining if no changes detected
- Training Celery task (hourly schedule via Beat)
- Model serialization to disk (pickle with version tracking)
- Format version for model compatibility checking
- Logging of training metrics (document count, feature count, accuracy)

### Task 13.3: Prediction & Suggestions
- ClassificationPlugin (order 100) for processing pipeline:
  - Load trained models
  - Vectorize document content
  - Predict tags, correspondent, type, storage path
  - Store suggestions in ProcessingContext
  - Apply if matching_algorithm == MATCH_AUTO
- Suggestions API: GET `/api/v1/documents/{id}/suggestions/`
  - Returns ranked suggestions with confidence scores
  - Separate lists for tags, correspondent, type, path
- Celery task for batch re-classification of existing documents

### Task 13.4: Matching Algorithm Integration
- Update matching.py to use classifier for MATCH_AUTO
- Predictions only applied to items marked MATCH_AUTO
- Fall back to regex/fuzzy/literal for non-AUTO items
- Configuration: auto-classification can be disabled globally

### Task 13.5: Frontend Suggestion UI
- Suggestion chips on document detail page
- "Accept" button per suggestion (one-click apply)
- "Accept all" button (apply all suggestions at once)
- "Dismiss" button (hide suggestion)
- Visual indicator: documents that need review (pending suggestions)
- Admin: classifier status page (last trained, document count, accuracy)

---

## Dependencies

### New Python Packages
```
scikit-learn>=1.7
nltk>=3.9
```

---

## Definition of Done
- [ ] Four classifiers train on MATCH_AUTO documents
- [ ] Smart retraining skips if no changes
- [ ] Content preprocessing with stemming and stop words works
- [ ] Classification plugin predicts in processing pipeline
- [ ] Predictions applied automatically for MATCH_AUTO items
- [ ] Suggestions API returns ranked predictions with confidence
- [ ] Frontend shows suggestion chips with accept/dismiss
- [ ] Classifier training runs hourly
- [ ] Redis caching for stemming works
- [ ] All features have unit tests
