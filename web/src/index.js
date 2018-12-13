import React from 'react';
import ReactDOM from 'react-dom';
import './index.css';
import App from './App';
import {Tree, attachActionsToAffects} from './Tree';
import registerServiceWorker from './registerServiceWorker';
import request from'request-promise-native';
import actionList from './structured_actions.json';

const useApp = false;
if (useApp) {
    let app = ReactDOM.render(<App/>, document.getElementById('root'));

    request.get({url: 'https://flow.corp.statestitle.com/api/action_list', json: true})
    // request.get({url: 'http://localhost:8000/api/action_list', json:true})
        .then(resp => {
            app.setState({actionList: resp})
        });
} else {
    ReactDOM.render(<Tree actionList={attachActionsToAffects(actionList)}/>, document.getElementById('root'))
}
registerServiceWorker();
