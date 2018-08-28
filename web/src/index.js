import React from 'react';
import ReactDOM from 'react-dom';
import './index.css';
import App from './App';
import registerServiceWorker from './registerServiceWorker';
import request from'request-promise-native';

let app = ReactDOM.render(<App />, document.getElementById('root'));

request.get({url: 'https://flow.corp.statestitle.com/api/action_list', json:true})
// request.get({url: 'http://localhost:8000/api/action_list', json:true})
    .then(resp => {
        app.setState({actionList: resp})
    });
registerServiceWorker();
