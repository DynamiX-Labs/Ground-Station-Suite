export const DEFAULT_RIG = {
    id: null,
    name: "",
    host: "localhost",
    port: 4532,
    radiotype: "rx",
    radio_mode: "duplex",
    tx_control_mode: "auto",
    retune_interval_ms: 2000,
};

export function validateRigForm(formValues, t) {
    const validationErrors = {};
    if (!formValues.name?.trim()) validationErrors.name = t("shared.required");
    if (!formValues.host?.trim()) validationErrors.host = t("shared.required");
    if (!formValues.port && formValues.port !== 0) {
        validationErrors.port = t("shared.required");
    } else if (Number(formValues.port) <= 0 || Number(formValues.port) > 65535) {
        validationErrors.port = t("shared.port_range");
    }
    if (!formValues.retune_interval_ms && formValues.retune_interval_ms !== 0) {
        validationErrors.retune_interval_ms = t("shared.required");
    } else if (
        Number(formValues.retune_interval_ms) < 100
        || Number(formValues.retune_interval_ms) > 60000
    ) {
        validationErrors.retune_interval_ms = t("rig.validation.retune_interval_range");
    }
    return validationErrors;
}
