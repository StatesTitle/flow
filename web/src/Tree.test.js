import React from 'react';
import ReactDOM from 'react-dom';
import {Tree, attachActionsToAffects} from "./Tree";

it('renders action list', () => {
    const div = document.createElement('div');
    const data = require('./structured_actions.json');
    ReactDOM.render(<Tree actionList={attachActionsToAffects(data)}/>, div);
    ReactDOM.unmountComponentAtNode(div);
});