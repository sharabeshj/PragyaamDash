import * as ActionTypes from '../Actions/Actions';

const LoginHandler = (state = { token : '',auth_token : '', orgId : '',userId : '', authenticated: false},action) => {
    switch(action.type){
        case ActionTypes.LOGIN_SUCCESS:
            return {
                ...state,
                authenticated: true,
                token : action.data.token,
                orgId : action.data.orgId,
                userId : action.data.userId,
                auth_token : action.data.auth_token,
            }
        case ActionTypes.LOGIN_ERROR:
            return {
                ...state,
                token : '',
                orgId : '',
                userId : '',
            }
        default:
            return {
                ...state
            }
    }
}

export default LoginHandler;