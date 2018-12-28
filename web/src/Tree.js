import React, { Component } from 'react';

function Field(props) {
    if (!props.value) {
        return null;
    } else if (props.length > 40) {
        return [<p className="font-weight-bold">{props.name}</p>, <p>{props.value}</p>];
    } else {
        return (<p><span className="font-weight-bold">{props.name}: </span>{props.value}</p>);
    }
}

function Email(props) {
    const email = props.email;
    return (<li className="list-group-item">
        <Field name="Email" value={email.name}/>
        <Field name="Subject" value={email.subject}/>
        <Field name="Body" value={email.body}/>
        <Field name="Attached Documents" value={email.documents.map(d => d.name).join(', ')}/>
        <Field name="Generated Templates" value={email.templates.map(t => t.name + " of type " + t.document_type.name).join(', ')}/>
        <Field name="Recipients" value={email.recipients.map(r => r.name).join(', ')}/>
        <Field name="Required Partners" value={email.required.map(r => r.name).join(', ')}/>
        <Field name="Excluded Partners" value={email.excluded.map(r => r.name).join(', ')}/>
        </li>);
}

function Affect(props) {
    return <li className="list-group-item">{props.affect.type} {props.affect.action.name}</li>;
}

function Action(props) {
    const action = props.action;
    return (<div className="card border-dark mb-1">
        <div className="card-header">{action.name}</div>
        {((action.required.length > 0 || action.excluded.length > 0) && (
        <div className="card-body">
            <Field name="Required Partners" value={action.required.map(r => r.name).join(', ')}/>
            <Field name="Excluded Partners" value={action.excluded.map(r => r.name).join(', ')}/>
        </div>))}
        <ul className="list-group list-group-flush">
            {action.start_affects.map(a => <Affect key={a.type + " " + a.task + " " + a.group_id + " " + a.action_id} affect={a}/>)}
            {action.start_emails.map(e => <Email key={e.task + " " + e.name} email={e}/>)}
            {action.complete_affects.map(a => <Affect key={a.type + " " + a.task + " " + a.group_id + " " + a.action_id} affect={a}/>)}
            {action.complete_emails.map(e => <Email key={e.task + " " + e.name} email={e}/>)}
        </ul>
    </div>);
}

function Group(props) {
    const group = props.group;
    return (<div className="card mb-2">
        <div className="card-header">{props.group.name}</div>
        <div className="card-body">
            <Field name="Required Partners" value={group.required.map(r => r.name).join(', ')}/>
            <Field name="Excluded Partners" value={group.excluded.map(r => r.name).join(', ')}/>
            {props.group.actions.map(a => <Action key={a.action_id} action={a} />)}
        </div>
        </div>);
}


function Tree(props) {
    return (<div className="container">
        {props.actionList.groups.map(g => <Group key={g.id} group={g} />)}
    </div>);
}

function attachActionsToAffects(actionList) {
        const actionLookup = {};
        actionList.groups.forEach(group => {
            const actionById = {};
            actionLookup[group.id] = actionById;
            group.actions.forEach(a => {actionById[a.action_id] = a});
        });
        function attach(possiblyIdContainingItems) {
            possiblyIdContainingItems.forEach(item => {
                if (!item.group_id || !item.action_id) {
                    return;
                }
                item.action = actionLookup[item.group_id][item.action_id];
            })
        }
        actionList.groups.forEach(group => {
            group.actions.forEach(action =>{
                attach(action.start_affects);
                attach(action.complete_affects);
            });
        });
        return actionList;
}

export {Tree, attachActionsToAffects};