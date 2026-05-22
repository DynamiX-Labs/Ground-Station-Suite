export const getSessions = (item) => (Array.isArray(item?.sessions) ? item.sessions : []);

export const getFlattenedTasks = (item) =>
    getSessions(item).flatMap((session) => (Array.isArray(session?.tasks) ? session.tasks : []));

export const getSessionSdrs = (item) =>
    getSessions(item)
        .map((session) => session?.sdr)
        .filter(Boolean);
