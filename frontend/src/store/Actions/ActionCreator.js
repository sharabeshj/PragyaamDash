import * as ActionTypes from './Actions';

export const workspaceAdd = (workspaceName) => {
    return {
        type : ActionTypes.WORKSPACE_ADD,
        workspaceName : workspaceName
    }
}

export const fieldAdd = fields => {
    return {
        type : ActionTypes.FIELD_ADD,
        fields : fields
    }
}