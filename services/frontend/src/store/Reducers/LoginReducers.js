import * as ActionTypes from '../Actions/Actions';

const LoginHandler = (state = { token : '', orgId : '',userId : ''},action) => {
    switch(action.type){
        case ActionTypes.LOGIN_SUCCESS:
            return {
                ...state,
                token : action.data.token,
                orgId : action.data.organizationId,
                userId : action.data.userId
            }
        case ActionTypes.LOGIN_ERROR:
            return {
                ...state,
                token : '',
                orgId : '',
                userId : ''
            }
        default:
            return {
                ...state
            }
    }
}

export default LoginHandler;