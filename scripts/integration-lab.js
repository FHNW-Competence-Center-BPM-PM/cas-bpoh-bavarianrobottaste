const integrationLabRoot = document.querySelector("[data-integration-lab]");

if (integrationLabRoot) {
  const AUTH_TOKEN_STORAGE_KEY = "bavarianRoboTasteAuthToken";
  const SOAP_ENV_NS = "http://schemas.xmlsoap.org/soap/envelope/";
  const CRM_NS = "http://bavarian-robotaste.local/crm";

  const targetSelect = integrationLabRoot.querySelector("[data-lab-target]");
  const operationSelect = integrationLabRoot.querySelector("[data-lab-operation]");
  const previewMethod = integrationLabRoot.querySelector("[data-lab-preview-method]");
  const previewUrl = integrationLabRoot.querySelector("[data-lab-preview-url]");
  const previewHeaders = integrationLabRoot.querySelector("[data-lab-preview-headers]");
  const previewBody = integrationLabRoot.querySelector("[data-lab-preview-body]");
  const responseStatus = integrationLabRoot.querySelector("[data-lab-response-status]");
  const responseTime = integrationLabRoot.querySelector("[data-lab-response-time]");
  const responseHeaders = integrationLabRoot.querySelector("[data-lab-response-headers]");
  const responseBody = integrationLabRoot.querySelector("[data-lab-response-body]");
  const sendButton = integrationLabRoot.querySelector("[data-lab-send]");
  const resetButton = integrationLabRoot.querySelector("[data-lab-reset]");
  const cmsNote = integrationLabRoot.querySelector("[data-lab-cms-note]");

  const fieldValue = (name) =>
    integrationLabRoot.querySelector(`[data-field="${name}"]`)?.value?.trim() || "";

  const fillTokenFromSession = () => {
    const tokenInput = integrationLabRoot.querySelector('[data-field="crmBearerToken"]');
    if (tokenInput && !tokenInput.value) {
      tokenInput.value = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) || "";
    }
  };

  const escapeXml = (value) =>
    String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&apos;");

  const formatJson = (value) => JSON.stringify(value, null, 2);

  const formatXml = (xml) => {
    const normalized = xml.replace(/>\s*</g, "><").trim();
    const parts = normalized.replace(/></g, ">\n<").split("\n");
    let indent = 0;

    return parts
      .map((part) => {
        if (part.match(/^<\//)) {
          indent = Math.max(indent - 1, 0);
        }
        const line = `${"  ".repeat(indent)}${part}`;
        if (part.match(/^<[^!?/][^>]*[^/]>/) && !part.includes("</")) {
          indent += 1;
        }
        return line;
      })
      .join("\n");
  };

  const xmlNode = (name, value) => `      <crm:${name}>${escapeXml(value)}</crm:${name}>`;

  const buildSoapEnvelope = (operation, innerLines) =>
    formatXml(`
<soapenv:Envelope xmlns:soapenv="${SOAP_ENV_NS}" xmlns:crm="${CRM_NS}">
  <soapenv:Body>
    <crm:${operation}>
${innerLines.join("\n")}
    </crm:${operation}>
  </soapenv:Body>
</soapenv:Envelope>`);

  const parseItemsJson = () => {
    const raw = fieldValue("crmInvoiceItems");
    if (!raw) {
      return [];
    }
    return JSON.parse(raw);
  };

  const operations = {
    cms: [
      { value: "cms-get", label: "GET Produkt nach ERP-ID" },
      { value: "cms-price", label: "PUT Preisupdate" },
    ],
    crm: [
      { value: "crm-id-by-email", label: "GetCustomerIdByEmail" },
      { value: "crm-reservations", label: "GetCustomerReservations" },
      { value: "crm-stats", label: "GetCustomerReservationStats" },
      { value: "crm-status", label: "UpdateReservationStatus" },
      { value: "crm-invoice", label: "UpsertCustomerInvoice" },
      { value: "crm-revenue", label: "GetCustomerRevenue" },
    ],
  };

  const visibleSectionsFor = (operation) => {
    const sections = ["crm-common"];
    if (operation.startsWith("cms-")) {
      return [operation];
    }
    sections.push(operation);
    return sections;
  };

  const setVisibleSections = (operation) => {
    integrationLabRoot.querySelectorAll("[data-lab-section]").forEach((section) => {
      section.hidden = !visibleSectionsFor(operation).includes(section.dataset.labSection);
    });
  };

  const buildRequest = () => {
    const operation = operationSelect.value;
    if (operation === "cms-get") {
      const erpId = encodeURIComponent(fieldValue("cmsGetErpId"));
      return {
        method: "GET",
        url: `/api/cms/products/${erpId}`,
        headers: { Accept: "application/json" },
        body: "",
      };
    }

    if (operation === "cms-price") {
      const erpId = encodeURIComponent(fieldValue("cmsPriceErpId"));
      return {
        method: "PUT",
        url: `/api/cms/products/${erpId}/price`,
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: formatJson({ price: fieldValue("cmsPriceValue") }),
      };
    }

    const baseHeaders = {
      Accept: "text/xml",
      "Content-Type": "text/xml; charset=utf-8",
    };
    const token = fieldValue("crmBearerToken");
    if (token) {
      baseHeaders.Authorization = `Bearer ${token}`;
    }

    if (operation === "crm-id-by-email") {
      return {
        method: "POST",
        url: "/api/crm/soap",
        headers: baseHeaders,
        body: buildSoapEnvelope("GetCustomerIdByEmail", [xmlNode("customerEmail", fieldValue("crmCustomerEmail"))]),
      };
    }

    if (operation === "crm-reservations") {
      return {
        method: "POST",
        url: "/api/crm/soap",
        headers: baseHeaders,
        body: buildSoapEnvelope("GetCustomerReservations", [
          xmlNode("customerId", fieldValue("crmReservationsCustomerId")),
        ]),
      };
    }

    if (operation === "crm-stats") {
      return {
        method: "POST",
        url: "/api/crm/soap",
        headers: baseHeaders,
        body: buildSoapEnvelope("GetCustomerReservationStats", [
          xmlNode("customerId", fieldValue("crmStatsCustomerId")),
        ]),
      };
    }

    if (operation === "crm-status") {
      return {
        method: "POST",
        url: "/api/crm/soap",
        headers: baseHeaders,
        body: buildSoapEnvelope("UpdateReservationStatus", [
          xmlNode("customerId", fieldValue("crmStatusCustomerId")),
          xmlNode("reservationId", fieldValue("crmStatusReservationId")),
          xmlNode("status", fieldValue("crmStatusValue")),
        ]),
      };
    }

    if (operation === "crm-invoice") {
      const items = parseItemsJson();
      const itemLines = items.length
        ? [
            "      <crm:items>",
            ...items.flatMap((item) => [
              "        <crm:item>",
              `          <crm:itemId>${escapeXml(item.itemId || "")}</crm:itemId>`,
              `          <crm:name>${escapeXml(item.name || "")}</crm:name>`,
              `          <crm:qty>${escapeXml(item.qty ?? 1)}</crm:qty>`,
              `          <crm:price>${escapeXml(item.price ?? 0)}</crm:price>`,
              "        </crm:item>",
            ]),
            "      </crm:items>",
          ]
        : [];

      return {
        method: "POST",
        url: "/api/crm/soap",
        headers: baseHeaders,
        body: buildSoapEnvelope("UpsertCustomerInvoice", [
          xmlNode("customerId", fieldValue("crmInvoiceCustomerId")),
          xmlNode("reservationId", fieldValue("crmInvoiceReservationId")),
          xmlNode("invoiceId", fieldValue("crmInvoiceId")),
          xmlNode("currency", fieldValue("crmInvoiceCurrency")),
          xmlNode("totalAmount", fieldValue("crmInvoiceTotalAmount")),
          xmlNode("paidAt", fieldValue("crmInvoicePaidAt")),
          ...itemLines,
        ]),
      };
    }

    return {
      method: "POST",
      url: "/api/crm/soap",
      headers: baseHeaders,
      body: buildSoapEnvelope("GetCustomerRevenue", [
        xmlNode("customerId", fieldValue("crmRevenueCustomerId")),
      ]),
    };
  };

  const populateOperationOptions = () => {
    const options = operations[targetSelect.value] || [];
    operationSelect.innerHTML = options
      .map((option) => `<option value="${option.value}">${option.label}</option>`)
      .join("");
  };

  const updatePreview = () => {
    try {
      const request = buildRequest();
      previewMethod.textContent = request.method;
      previewUrl.textContent = request.url;
      previewHeaders.value = Object.entries(request.headers)
        .map(([key, value]) => `${key}: ${value}`)
        .join("\n");
      previewBody.value = request.body;
      responseStatus.textContent = "Bereit";
      responseTime.textContent = "Request generiert";
    } catch (error) {
      previewMethod.textContent = "Fehler";
      previewUrl.textContent = "-";
      previewHeaders.value = "";
      previewBody.value = error.message || String(error);
    }
  };

  const syncUi = () => {
    setVisibleSections(operationSelect.value);
    if (cmsNote) {
      cmsNote.hidden = targetSelect.value !== "cms";
    }
    updatePreview();
  };

  const sendRequest = async () => {
    let request;
    try {
      request = {
        ...buildRequest(),
        body: previewBody.value,
      };
    } catch (error) {
      responseStatus.textContent = "Lokaler Fehler";
      responseTime.textContent = "Request nicht gesendet";
      responseHeaders.value = "";
      responseBody.value = error.message || String(error);
      return;
    }

    responseStatus.textContent = "Laeuft";
    responseTime.textContent = "Sende Request ...";
    responseHeaders.value = "";
    responseBody.value = "";
    sendButton.disabled = true;

    const startedAt = performance.now();

    try {
      const fetchOptions = {
        method: request.method,
        headers: request.headers,
      };
      if (request.method !== "GET" && request.body) {
        fetchOptions.body = request.body;
      }

      const response = await fetch(request.url, fetchOptions);
      const text = await response.text();
      const elapsed = Math.round(performance.now() - startedAt);

      responseStatus.textContent = `${response.status} ${response.statusText}`;
      responseTime.textContent = `${elapsed} ms`;
      responseHeaders.value = Array.from(response.headers.entries())
        .map(([key, value]) => `${key}: ${value}`)
        .join("\n");

      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        try {
          responseBody.value = JSON.stringify(JSON.parse(text), null, 2);
        } catch (_) {
          responseBody.value = text;
        }
      } else if (contentType.includes("xml") || text.trim().startsWith("<")) {
        responseBody.value = formatXml(text);
      } else {
        responseBody.value = text;
      }
    } catch (error) {
      responseStatus.textContent = "Netzwerkfehler";
      responseTime.textContent = "Request fehlgeschlagen";
      responseHeaders.value = "";
      responseBody.value = error.message || String(error);
    } finally {
      sendButton.disabled = false;
    }
  };

  fillTokenFromSession();
  populateOperationOptions();
  syncUi();

  targetSelect.addEventListener("change", () => {
    populateOperationOptions();
    syncUi();
  });

  operationSelect.addEventListener("change", syncUi);
  integrationLabRoot.addEventListener("input", updatePreview);
  resetButton.addEventListener("click", updatePreview);
  sendButton.addEventListener("click", sendRequest);
}
