import * as React from "react";
import { useDispatch } from "react-redux";
import { useSocket } from "../common/socket.jsx";
import { submitOrEditRig } from "../hardware/rig-slice.jsx";
import { toast } from "../../utils/toast-with-timestamp.jsx";
import { useTranslation } from "react-i18next";
import RigEditDialog from "../hardware/rig-edit-dialog.jsx";
import { DEFAULT_RIG, validateRigForm } from "../hardware/rig-edit-logic.js";

export default function RigQuickEditDialog({ open, onClose, rig }) {
    const dispatch = useDispatch();
    const { socket } = useSocket();
    const { t } = useTranslation("hardware");
    const [formValues, setFormValues] = React.useState(DEFAULT_RIG);
    const [saving, setSaving] = React.useState(false);

    React.useEffect(() => {
        if (!open) return;
        setFormValues({
            ...DEFAULT_RIG,
            ...(rig || {}),
        });
    }, [open, rig]);

    const handleChange = React.useCallback((event) => {
        const { name, value, type } = event.target;
        const nextValue = type === "number" ? Number(value) : value;
        setFormValues((previous) => ({
            ...previous,
            [name]: nextValue,
        }));
    }, []);

    const validationErrors = React.useMemo(() => validateRigForm(formValues, t), [formValues, t]);
    const hasValidationErrors = Object.keys(validationErrors).length > 0;

    const handleSubmit = React.useCallback(async () => {
        if (!socket || !formValues?.id) {
            return;
        }
        setSaving(true);
        try {
            await dispatch(submitOrEditRig({ socket, formValues })).unwrap();
            toast.success(t("rig.edited_success"), { autoClose: 5000 });
            onClose();
        } catch (error) {
            toast.error(`${t("rig.error_editing")}: ${error?.message || error}`, { autoClose: 5000 });
        } finally {
            setSaving(false);
        }
    }, [dispatch, formValues, onClose, socket, t]);

    return (
        <RigEditDialog
            open={open}
            onClose={onClose}
            isEditing
            formValues={formValues}
            validationErrors={validationErrors}
            hasValidationErrors={hasValidationErrors}
            loading={saving}
            onChange={handleChange}
            onSubmit={handleSubmit}
        />
    );
}
