import { createStore, applyMiddleware } from 'redux';
import thunkMiddleware from 'redux-thunk';
import { createLogger } from 'redux-logger';
import RootReducer from './Reducers/RootReducers';

const loggerMiddleware = createLogger();

const ConfigureStore = state => {
    return createStore(
        RootReducer,
        state,
        applyMiddleware(
            thunkMiddleware,
            loggerMiddleware
        )
    )
}

export default ConfigureStore;