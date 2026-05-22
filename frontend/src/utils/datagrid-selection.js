export const toSelectedIds = (selectionModel) => {
    if (Array.isArray(selectionModel)) {
        return selectionModel;
    }

    if (selectionModel?.ids instanceof Set) {
        return Array.from(selectionModel.ids);
    }

    return [];
};

export const toRowSelectionModel = (selectedIds) => ({
    type: 'include',
    ids: new Set(selectedIds || []),
});
