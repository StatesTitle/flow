import React from 'react';
import ReactDOM from 'react-dom';
import Tree from './Tree';

it('renders action list', () => {
    const div = document.createElement('div');
    const data = require('./structured_actions.json');
    ReactDOM.render(<Tree actionList={data}/>, div);
    ReactDOM.unmountComponentAtNode(div);
});