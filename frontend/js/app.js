/**
 * MedLens Clinical Intelligence Platform — Client Application
 * Handles reactive state, API interactions, dynamic FHIR rendering,
 * and multimodal report visualization.
 */

class MedLensApp {
  constructor() {
    this.currentBundle = null;
    this.activeFilter = 'all';
    this.searchQuery = '';
    this.activeTab = 'preview-tab';
    this.currentRawText = '';
    this.currentDocName = 'sample_thyroid_panel.pdf';

    this.initElements();
    this.bindEvents();
    this.loadScenario('thyroid');
  }

  initElements() {
    // Buttons & Navigation
    this.btnThyroid = document.getElementById('btn-load-thyroid');
    this.btnCmp = document.getElementById('btn-load-cmp');
    this.btnCbc = document.getElementById('btn-load-cbc');
    this.btnViewFhir = document.getElementById('btn-view-fhir');
    this.btnReset = document.getElementById('btn-reset-session');

    // Left Pane
    this.currentDocBadge = document.getElementById('current-doc-name');
    this.dropzone = document.getElementById('file-dropzone');
    this.fileInput = document.getElementById('file-input');
    this.btnBrowse = document.getElementById('btn-browse-file');
    this.dropzoneLoader = document.getElementById('dropzone-loader');
    this.docPaperBody = document.getElementById('paper-body-content');
    this.docLabTitle = document.getElementById('paper-lab-title');
    this.docMetaInfo = document.getElementById('paper-meta-info');
    this.rawTextContent = document.getElementById('raw-text-content');
    this.auditStreamContent = document.getElementById('audit-stream-content');
    this.tabButtons = document.querySelectorAll('.tab-btn');

    // Right Pane - Patient Profile
    this.ptAvatar = document.getElementById('pt-avatar');
    this.ptName = document.getElementById('pt-name');
    this.ptDemographic = document.getElementById('pt-demographic');
    this.ptProvenance = document.getElementById('pt-provenance');
    this.ptSymptomsChips = document.getElementById('pt-symptoms-chips');
    this.ptConditionsChips = document.getElementById('pt-conditions-chips');
    this.ptAllergiesChips = document.getElementById('pt-allergies-chips');
    this.ptMedicationsChips = document.getElementById('pt-medications-chips');
    this.btnEditIntake = document.getElementById('btn-edit-intake');

    // Right Pane - Inconsistencies
    this.inconsistencyContainer = document.getElementById('inconsistency-alerts-container');

    // Right Pane - Observations Table
    this.obsCountBadge = document.getElementById('obs-count-badge');
    this.obsSearchInput = document.getElementById('obs-search-input');
    this.filterButtons = document.querySelectorAll('.filter-btn');
    this.obsTbody = document.getElementById('observations-tbody');

    // Right Pane - Non-Diagnostic AI Summary
    this.summaryHeadline = document.getElementById('summary-headline-text');
    this.summaryOverview = document.getElementById('summary-overview-content');
    this.summaryFlaggedGrid = document.getElementById('summary-flagged-grid');
    this.summaryQuestionsList = document.getElementById('summary-questions-list');
    this.btnCopySummary = document.getElementById('btn-copy-summary');

    // Modals
    this.modalIntake = document.getElementById('modal-intake');
    this.formEditIntake = document.getElementById('form-edit-intake');
    this.btnCloseIntake = document.getElementById('btn-close-intake');
    this.btnCancelIntake = document.getElementById('btn-cancel-intake');

    this.modalEditObs = document.getElementById('modal-edit-obs');
    this.formEditObs = document.getElementById('form-edit-obs');
    this.editObsTitle = document.getElementById('edit-obs-title');
    this.editObsId = document.getElementById('edit-obs-id');
    this.editObsVal = document.getElementById('edit-obs-val');
    this.editObsRange = document.getElementById('edit-obs-range');
    this.btnCloseObsModal = document.getElementById('btn-close-obs-modal');
    this.btnCancelObs = document.getElementById('btn-cancel-obs');

    this.modalFhir = document.getElementById('modal-fhir-bundle');
    this.fhirJsonCode = document.getElementById('fhir-json-code');
    this.btnCloseFhir = document.getElementById('btn-close-fhir-modal');
    this.btnCopyFhir = document.getElementById('btn-copy-fhir');
    this.btnDownloadFhir = document.getElementById('btn-download-fhir');

    // Popover
    this.popover = document.getElementById('provenance-popover');
    this.popoverTag = document.getElementById('popover-tag-label');
    this.popoverConf = document.getElementById('popover-conf-label');
    this.popoverFile = document.getElementById('popover-source-file');
    this.popoverPage = document.getElementById('popover-source-page');
    this.popoverSnippet = document.getElementById('popover-snippet-text');
  }

  bindEvents() {
    // Scenario Buttons
    this.btnThyroid.addEventListener('click', () => this.loadScenario('thyroid'));
    this.btnCmp.addEventListener('click', () => this.loadScenario('cmp'));
    this.btnCbc.addEventListener('click', () => this.loadScenario('cbc'));

    // Reset
    this.btnReset.addEventListener('click', () => this.resetSession());

    // Tabs
    this.tabButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.tabButtons.forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        btn.classList.add('active');
        const tabId = btn.getAttribute('data-tab');
        document.getElementById(tabId).classList.add('active');
      });
    });

    // File Upload
    this.btnBrowse.addEventListener('click', (e) => {
      e.stopPropagation();
      this.fileInput.click();
    });
    this.dropzone.addEventListener('click', () => this.fileInput.click());
    this.fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        this.uploadFile(e.target.files[0]);
      }
    });

    // Drag and Drop
    ['dragenter', 'dragover'].forEach(name => {
      this.dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        this.dropzone.classList.add('drag-over');
      });
    });
    ['dragleave', 'drop'].forEach(name => {
      this.dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        this.dropzone.classList.remove('drag-over');
      });
    });
    this.dropzone.addEventListener('drop', (e) => {
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        this.uploadFile(e.dataTransfer.files[0]);
      }
    });

    // Filters & Search
    this.obsSearchInput.addEventListener('input', (e) => {
      this.searchQuery = e.target.value.toLowerCase().trim();
      this.renderObservationsTable();
    });

    this.filterButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        this.filterButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.activeFilter = btn.getAttribute('data-filter');
        this.renderObservationsTable();
      });
    });

    // Intake Modal
    this.btnEditIntake.addEventListener('click', () => this.openIntakeModal());
    this.btnCloseIntake.addEventListener('click', () => this.modalIntake.classList.add('hidden'));
    this.btnCancelIntake.addEventListener('click', () => this.modalIntake.classList.add('hidden'));
    this.formEditIntake.addEventListener('submit', (e) => this.handleSaveIntake(e));

    // Observation Edit Modal
    this.btnCloseObsModal.addEventListener('click', () => this.modalEditObs.classList.add('hidden'));
    this.btnCancelObs.addEventListener('click', () => this.modalEditObs.classList.add('hidden'));
    this.formEditObs.addEventListener('submit', (e) => this.handleSaveObsEdit(e));

    // FHIR Modal
    this.btnViewFhir.addEventListener('click', () => this.openFhirModal());
    this.btnCloseFhir.addEventListener('click', () => this.modalFhir.classList.add('hidden'));
    this.btnCopyFhir.addEventListener('click', () => this.copyFhirJson());
    this.btnDownloadFhir.addEventListener('click', () => this.downloadFhirJson());

    // Copy Summary
    this.btnCopySummary.addEventListener('click', () => this.copySummaryText());
  }

  async loadScenario(name) {
    [this.btnThyroid, this.btnCmp, this.btnCbc].forEach(b => b.classList.remove('active'));
    if (name === 'thyroid') this.btnThyroid.classList.add('active');
    if (name === 'cmp') this.btnCmp.classList.add('active');
    if (name === 'cbc') this.btnCbc.classList.add('active');

    try {
      const resp = await fetch(`/api/load-sample/${name}`, { method: 'POST' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();

      this.currentDocName = data.filename;
      this.currentDocBadge.textContent = data.filename;
      this.currentRawText = data.raw_text;
      this.currentBundle = data.bundle;

      this.renderAll();
    } catch (err) {
      console.error('Failed to load sample scenario:', err);
      alert('Error loading scenario: ' + err.message);
    }
  }

  async uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    this.dropzoneLoader.classList.remove('hidden');

    try {
      const resp = await fetch('/api/extract', {
        method: 'POST',
        body: formData,
      });

      if (!resp.ok) {
        const errorData = await resp.json();
        throw new Error(errorData.detail || `Upload failed with status ${resp.status}`);
      }

      const data = await resp.json();
      this.currentDocName = data.filename;
      this.currentDocBadge.textContent = data.filename;
      this.currentRawText = data.raw_text;
      this.currentBundle = data.bundle;

      this.renderAll();
    } catch (err) {
      alert(`Extraction Error: ${err.message}`);
    } finally {
      this.dropzoneLoader.classList.add('hidden');
      this.fileInput.value = '';
    }
  }

  async resetSession() {
    if (!confirm('Reset current clinical workspace to initial state?')) return;
    try {
      const resp = await fetch('/api/reset', { method: 'POST' });
      const data = await resp.json();
      this.currentBundle = data.bundle;
      this.renderAll();
    } catch (err) {
      alert('Reset failed: ' + err.message);
    }
  }

  renderAll() {
    if (!this.currentBundle) return;
    this.renderPatientIntake();
    this.renderInconsistencies();
    this.renderObservationsTable();
    this.renderSummary();
    this.renderDocumentViewer();
    this.renderRawText();
    this.renderAuditStream();
  }

  renderPatientIntake() {
    const pt = this.currentBundle.patient;
    if (!pt) return;

    // Avatar initials
    const initials = pt.id.includes('thyroid') ? 'JD' : (pt.id.includes('cmp') ? 'JS' : (pt.id.includes('cbc') ? 'ED' : 'PT'));
    const name = pt.id.includes('thyroid') ? 'Jane Doe' : (pt.id.includes('cmp') ? 'Johnathan Smith' : (pt.id.includes('cbc') ? 'Emily Davis' : 'Active Patient'));

    this.ptAvatar.textContent = initials;
    this.ptName.textContent = name;
    this.ptDemographic.textContent = `${pt.age} yrs • ${pt.sex}`;
    this.ptProvenance.textContent = pt.provenance ? pt.provenance.source_type : '[User Provided]';

    // Symptoms
    this.ptSymptomsChips.innerHTML = pt.symptoms.length
      ? pt.symptoms.map(s => `<span class="chip chip-subtle">${this.escapeHtml(s)}</span>`).join('')
      : '<span class="chip chip-subtle">None reported</span>';

    // Conditions
    this.ptConditionsChips.innerHTML = pt.conditions.length
      ? pt.conditions.map(c => `<span class="chip chip-subtle">${this.escapeHtml(c)}</span>`).join('')
      : '<span class="chip chip-subtle">None documented</span>';

    // Allergies
    this.ptAllergiesChips.innerHTML = pt.allergies.length
      ? pt.allergies.map(a => `<span class="chip chip-danger">⚠ ${this.escapeHtml(a)}</span>`).join('')
      : '<span class="chip chip-subtle">NKDA (No Known Allergies)</span>';

    // Medications
    this.ptMedicationsChips.innerHTML = pt.medications.length
      ? pt.medications.map(m => `<span class="chip chip-accent">💊 ${this.escapeHtml(m)}</span>`).join('')
      : '<span class="chip chip-subtle">No medications reported</span>';
  }

  renderInconsistencies() {
    const incs = this.currentBundle.inconsistencies || [];
    this.inconsistencyContainer.innerHTML = '';

    if (incs.length === 0) {
      this.inconsistencyContainer.innerHTML = `
        <div class="inconsistency-card inconsistency-info" style="border-left-color: #10b981;">
          <div class="inconsistency-header">
            <div class="inconsistency-title-wrap">
              <span class="inconsistency-badge" style="background: #10b981; color: white;">CLEAN</span>
              <h3 class="inconsistency-title">No Clinical Inconsistencies Detected</h3>
            </div>
          </div>
          <p class="inconsistency-desc">Patient reported medical history, active medications, and extracted laboratory observations are clinically concordant.</p>
        </div>
      `;
      return;
    }

    incs.forEach(inc => {
      const card = document.createElement('div');
      const sevClass = inc.severity === 'CRITICAL' ? 'inconsistency-critical' : (inc.severity === 'WARNING' ? 'inconsistency-warning' : 'inconsistency-info');
      const badgeClass = inc.severity === 'CRITICAL' ? 'badge-critical' : (inc.severity === 'WARNING' ? 'badge-warning' : 'badge-info');

      card.className = `inconsistency-card ${sevClass}`;
      card.innerHTML = `
        <div class="inconsistency-header">
          <div class="inconsistency-title-wrap">
            <span class="inconsistency-badge ${badgeClass}">${inc.severity}</span>
            <h3 class="inconsistency-title">${this.escapeHtml(inc.title)}</h3>
          </div>
          <span class="file-name-badge">${this.escapeHtml(inc.category)}</span>
        </div>
        <p class="inconsistency-desc">${this.escapeHtml(inc.description)}</p>
        <div class="conflicting-elements-box">
          ${inc.conflicting_elements.map(el => `<div class="conflicting-element-item">${this.escapeHtml(el)}</div>`).join('')}
        </div>
        <div class="clinician-action-row">
          <div class="action-text"><strong>Clinician Action:</strong> ${this.escapeHtml(inc.clinician_action)}</div>
          <button class="btn btn-sm ${inc.is_reviewed ? 'btn-ghost' : 'btn-outline'}" data-ack-id="${inc.id}">
            ${inc.is_reviewed ? '✓ Reviewed & Acknowledged' : 'Acknowledge Discrepancy'}
          </button>
        </div>
      `;

      const ackBtn = card.querySelector(`[data-ack-id="${inc.id}"]`);
      if (ackBtn && !inc.is_reviewed) {
        ackBtn.addEventListener('click', () => this.acknowledgeInconsistency(inc.id));
      }

      this.inconsistencyContainer.appendChild(card);
    });
  }

  async acknowledgeInconsistency(incId) {
    try {
      const resp = await fetch(`/api/inconsistency/${incId}/acknowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: 'Reviewed by attending physician. Documenting reconciliation in clinical record.' }),
      });
      if (!resp.ok) throw new Error('Acknowledge failed');
      
      // Update local state
      const inc = this.currentBundle.inconsistencies.find(i => i.id === incId);
      if (inc) inc.is_reviewed = true;
      this.renderInconsistencies();
    } catch (err) {
      alert(err.message);
    }
  }

  renderObservationsTable() {
    const obsList = this.currentBundle.observations || [];
    this.obsCountBadge.textContent = `${obsList.length} Tests`;

    // Filter and search
    const filtered = obsList.filter(obs => {
      // Search
      const name = (obs.code.text || '').toLowerCase();
      const code = (obs.code.coding && obs.code.coding[0] ? obs.code.coding[0].code || '' : '').toLowerCase();
      const matchesSearch = !this.searchQuery || name.includes(this.searchQuery) || code.includes(this.searchQuery);

      // Filter
      let matchesFilter = true;
      if (this.activeFilter === 'flagged') {
        matchesFilter = obs.interpretation === 'HIGH' || obs.interpretation === 'LOW' || obs.interpretation === 'UNSPECIFIED';
      } else if (this.activeFilter !== 'all') {
        matchesFilter = obs.interpretation === this.activeFilter;
      }

      return matchesSearch && matchesFilter;
    });

    this.obsTbody.innerHTML = '';

    if (filtered.length === 0) {
      this.obsTbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; padding: 24px; color: var(--text-muted);">
            No laboratory observations match the selected criteria.
          </td>
        </tr>
      `;
      return;
    }

    filtered.forEach(obs => {
      const tr = document.createElement('tr');
      const testName = obs.code.text;
      const loinc = obs.code.coding && obs.code.coding[0] && obs.code.coding[0].system === 'http://loinc.org' ? obs.code.coding[0].code : null;

      const val = obs.valueQuantity ? obs.valueQuantity.value : (obs.valueString || '—');
      const unit = obs.valueQuantity ? obs.valueQuantity.unit : '';

      let rangeText = 'None (Unspecified)';
      if (obs.referenceRange && obs.referenceRange[0]) {
        const r = obs.referenceRange[0];
        rangeText = r.text || (r.low !== null && r.high !== null ? `${r.low} - ${r.high}` : (r.high !== null ? `< ${r.high}` : (r.low !== null ? `> ${r.low}` : 'None')));
      }

      const interp = obs.interpretation || 'UNSPECIFIED';
      const provenanceTag = obs.provenance ? obs.provenance.source_type : '[Extracted from Lab PDF]';

      tr.innerHTML = `
        <td>
          <div class="test-name-cell">
            <span class="test-name-text">${this.escapeHtml(testName)}</span>
            ${loinc ? `<span class="loinc-badge">LOINC: ${this.escapeHtml(loinc)}</span>` : ''}
          </div>
        </td>
        <td class="value-cell">
          <span>${val}</span>
          <span class="value-unit">${this.escapeHtml(unit)}</span>
        </td>
        <td class="range-cell">${this.escapeHtml(rangeText)}</td>
        <td>
          <span class="interp-badge interp-${interp}">
            ${interp === 'HIGH' ? '▲ HIGH' : (interp === 'LOW' ? '▼ LOW' : (interp === 'NORMAL' ? '● NORMAL' : '○ UNSPECIFIED'))}
          </span>
        </td>
        <td>
          <button class="provenance-pill-btn" data-prov-id="${obs.id}">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            ${this.escapeHtml(provenanceTag)}
          </button>
        </td>
        <td>
          <button class="btn btn-sm btn-ghost" data-edit-id="${obs.id}" title="Edit value inline">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 20h9"/>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
            </svg>
          </button>
        </td>
      `;

      // Provenance popover hover
      const provBtn = tr.querySelector(`[data-prov-id="${obs.id}"]`);
      if (provBtn) {
        provBtn.addEventListener('mouseenter', (e) => this.showProvenancePopover(e, obs));
        provBtn.addEventListener('mouseleave', () => this.hideProvenancePopover());
      }

      // Edit click
      const editBtn = tr.querySelector(`[data-edit-id="${obs.id}"]`);
      if (editBtn) {
        editBtn.addEventListener('click', () => this.openEditObsModal(obs));
      }

      this.obsTbody.appendChild(tr);
    });
  }

  showProvenancePopover(event, obs) {
    const rect = event.currentTarget.getBoundingClientRect();
    const prov = obs.provenance;

    this.popoverTag.textContent = prov.source_type || '[Extracted from Lab PDF]';
    this.popoverConf.textContent = `Confidence: ${(prov.confidence_score * 100).toFixed(0)}%`;
    this.popoverFile.textContent = prov.source_file || this.currentDocName;
    this.popoverPage.textContent = `Page ${prov.page_number || 1}`;
    this.popoverSnippet.textContent = prov.raw_snippet || 'No raw snippet available';

    this.popover.style.top = `${rect.bottom + window.scrollY + 6}px`;
    this.popover.style.left = `${Math.min(rect.left + window.scrollX - 40, window.innerWidth - 320)}px`;
    this.popover.classList.remove('hidden');
    this.popover.style.display = 'flex';
  }

  hideProvenancePopover() {
    this.popover.classList.add('hidden');
    this.popover.style.display = 'none';
  }

  renderSummary() {
    const summary = this.currentBundle.summary;
    if (!summary) return;

    this.summaryHeadline.textContent = summary.headline;
    this.summaryOverview.textContent = summary.overview;

    // Flagged Findings Grid
    this.summaryFlaggedGrid.innerHTML = '';
    if (!summary.flagged_findings || summary.flagged_findings.length === 0) {
      this.summaryFlaggedGrid.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 12px; background: rgba(16, 185, 129, 0.08); border-radius: var(--radius-sm); color: #34d399; font-size: 0.8rem;">
          ✓ All extracted observations are within normal laboratory reference limits.
        </div>
      `;
    } else {
      summary.flagged_findings.forEach(ff => {
        const card = document.createElement('div');
        card.className = 'flagged-finding-card';
        card.style.borderLeftColor = ff.interpretation === 'HIGH' ? '#f43f5e' : (ff.interpretation === 'LOW' ? '#0ea5e9' : '#94a3b8');

        card.innerHTML = `
          <div class="flagged-card-header">
            <span class="flagged-test-name">${this.escapeHtml(ff.test_name)}</span>
            <span class="interp-badge interp-${ff.interpretation}">${ff.interpretation}</span>
          </div>
          <div class="flagged-val-text">
            Reported: <strong>${this.escapeHtml(ff.value)} ${this.escapeHtml(ff.unit)}</strong>
          </div>
          <div class="flagged-context-text">${this.escapeHtml(ff.clinical_context)}</div>
          <div class="flagged-ref-range">Reference Range: ${this.escapeHtml(ff.reference_range)}</div>
        `;
        this.summaryFlaggedGrid.appendChild(card);
      });
    }

    // Questions for Doctor
    this.summaryQuestionsList.innerHTML = (summary.discussion_points || [])
      .map(q => `<li>${this.escapeHtml(q)}</li>`)
      .join('');
  }

  renderDocumentViewer() {
    const obsList = this.currentBundle.observations || [];
    const pt = this.currentBundle.patient;

    this.docLabTitle.textContent = this.currentDocName.toUpperCase().replace('.PDF', '').replace('.TXT', '').replace(/_/g, ' ');
    this.docMetaInfo.innerHTML = `
      <span><strong>Patient:</strong> ${this.escapeHtml(pt ? `${this.ptName.textContent} (${pt.age}y, ${pt.sex})` : 'Active Patient')}</span>
      <span><strong>File:</strong> ${this.escapeHtml(this.currentDocName)}</span>
      <span><strong>Observations Parsed:</strong> ${obsList.length}</span>
      <span><strong>Audit Status:</strong> Verified Deterministic</span>
    `;

    // Simulated high-fidelity lab paper view
    let tableHtml = `
      <table class="paper-table">
        <thead>
          <tr>
            <th>Test Name</th>
            <th>Result</th>
            <th>Flag</th>
            <th>Reference Interval</th>
            <th>Units</th>
          </tr>
        </thead>
        <tbody>
    `;

    obsList.forEach(obs => {
      const val = obs.valueQuantity ? obs.valueQuantity.value : (obs.valueString || '—');
      const unit = obs.valueQuantity ? obs.valueQuantity.unit : '';
      const interp = obs.interpretation;
      const flagClass = interp === 'HIGH' ? 'paper-flag-high' : (interp === 'LOW' ? 'paper-flag-low' : '');
      const flagText = interp === 'HIGH' ? 'H' : (interp === 'LOW' ? 'L' : '');

      let range = 'None';
      if (obs.referenceRange && obs.referenceRange[0]) {
        range = obs.referenceRange[0].text || (obs.referenceRange[0].low !== null && obs.referenceRange[0].high !== null ? `${obs.referenceRange[0].low} - ${obs.referenceRange[0].high}` : 'None');
      }

      tableHtml += `
        <tr class="${flagClass}">
          <td><strong>${this.escapeHtml(obs.code.text)}</strong></td>
          <td>${val}</td>
          <td>${flagText}</td>
          <td>${this.escapeHtml(range)}</td>
          <td>${this.escapeHtml(unit)}</td>
        </tr>
      `;
    });

    tableHtml += `</tbody></table>`;
    this.docPaperBody.innerHTML = tableHtml;
  }

  renderRawText() {
    this.rawTextContent.textContent = this.currentRawText || 'No raw document text available.';
  }

  renderAuditStream() {
    const obsList = this.currentBundle.observations || [];
    this.auditStreamContent.innerHTML = '';

    obsList.forEach(obs => {
      const p = obs.provenance;
      const item = document.createElement('div');
      item.className = 'audit-item';
      item.innerHTML = `
        <div class="audit-header">
          <span class="audit-test-name">${this.escapeHtml(obs.code.text)} (${obs.id})</span>
          <span class="audit-score">Confidence: ${(p.confidence_score * 100).toFixed(0)}%</span>
        </div>
        <div>Origin: <strong>${this.escapeHtml(p.source_type)}</strong> • File: ${this.escapeHtml(p.source_file || this.currentDocName)} (Page ${p.page_number || 1})</div>
        <div class="audit-snippet">Snippet: "${this.escapeHtml(p.raw_snippet || '')}"</div>
      `;
      this.auditStreamContent.appendChild(item);
    });
  }

  // =========================================================================
  // Modals & Handlers
  // =========================================================================
  openIntakeModal() {
    const pt = this.currentBundle.patient;
    document.getElementById('intake-age').value = pt.age;
    document.getElementById('intake-sex').value = pt.sex;
    document.getElementById('intake-symptoms').value = pt.symptoms.join(', ');
    document.getElementById('intake-conditions').value = pt.conditions.join(', ');
    document.getElementById('intake-allergies').value = pt.allergies.join(', ');
    document.getElementById('intake-medications').value = pt.medications.join(', ');

    this.modalIntake.classList.remove('hidden');
  }

  async handleSaveIntake(e) {
    e.preventDefault();
    const payload = {
      age: parseInt(document.getElementById('intake-age').value, 10),
      sex: document.getElementById('intake-sex').value,
      symptoms: document.getElementById('intake-symptoms').value.split(',').map(s => s.trim()).filter(Boolean),
      conditions: document.getElementById('intake-conditions').value.split(',').map(s => s.trim()).filter(Boolean),
      allergies: document.getElementById('intake-allergies').value.split(',').map(s => s.trim()).filter(Boolean),
      medications: document.getElementById('intake-medications').value.split(',').map(s => s.trim()).filter(Boolean),
    };

    try {
      const resp = await fetch('/api/intake', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error('Failed to update patient intake');
      this.currentBundle = await resp.json();
      this.modalIntake.classList.add('hidden');
      this.renderAll();
    } catch (err) {
      alert(err.message);
    }
  }

  openEditObsModal(obs) {
    this.editObsTitle.textContent = `Edit Observation: ${obs.code.text}`;
    this.editObsId.value = obs.id;
    this.editObsVal.value = obs.valueQuantity ? obs.valueQuantity.value : '';

    let rangeText = '';
    if (obs.referenceRange && obs.referenceRange[0]) {
      rangeText = obs.referenceRange[0].text || '';
    }
    this.editObsRange.value = rangeText;

    this.modalEditObs.classList.remove('hidden');
  }

  async handleSaveObsEdit(e) {
    e.preventDefault();
    const obsId = this.editObsId.value;
    const val = parseFloat(this.editObsVal.value);
    const rangeText = this.editObsRange.value.trim() || null;

    try {
      const resp = await fetch(`/api/observation/${obsId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: val, reference_range_text: rangeText }),
      });
      if (!resp.ok) throw new Error('Update failed');

      // Refresh full bundle
      const bundleResp = await fetch('/api/bundle');
      this.currentBundle = await bundleResp.json();
      this.modalEditObs.classList.add('hidden');
      this.renderAll();
    } catch (err) {
      alert(err.message);
    }
  }

  async openFhirModal() {
    try {
      const resp = await fetch('/api/bundle');
      const data = await resp.json();
      this.fhirJsonCode.textContent = JSON.stringify(data, null, 2);
      this.modalFhir.classList.remove('hidden');
    } catch (err) {
      alert('Error fetching FHIR bundle: ' + err.message);
    }
  }

  copyFhirJson() {
    navigator.clipboard.writeText(this.fhirJsonCode.textContent).then(() => {
      this.btnCopyFhir.textContent = '✓ Copied!';
      setTimeout(() => (this.btnCopyFhir.textContent = 'Copy JSON'), 2000);
    });
  }

  downloadFhirJson() {
    const jsonStr = this.fhirJsonCode.textContent;
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fhir-bundle-${this.currentBundle ? this.currentBundle.id : 'export'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  copySummaryText() {
    if (!this.currentBundle || !this.currentBundle.summary) return;
    const s = this.currentBundle.summary;
    let text = `${s.headline}\n\n${s.overview}\n\nFLAGGED FINDINGS:\n`;
    s.flagged_findings.forEach(f => {
      text += `• ${f.test_name}: ${f.value} ${f.unit} (${f.interpretation}) [Ref: ${f.reference_range}]\n  Context: ${f.clinical_context}\n`;
    });
    text += `\nQUESTIONS FOR CLINICIAN:\n`;
    s.discussion_points.forEach(q => {
      text += `• ${q}\n`;
    });
    text += `\n${s.safety_disclaimer}\n`;

    navigator.clipboard.writeText(text).then(() => {
      this.btnCopySummary.innerHTML = `✓ Copied!`;
      setTimeout(() => {
        this.btnCopySummary.innerHTML = `
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg> Copy Summary
        `;
      }, 2000);
    });
  }

  escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

// Start application on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.medlens = new MedLensApp();
});
