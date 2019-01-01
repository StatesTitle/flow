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
        return (<span>
            <span className="font-weight-bold">On</span> {props.reason}
            <span className="font-weight-bold"> {props.affect.type}</span> {props.affect.action.name}
        </span>);
}

function Action(props) {
    const action = props.action;
    function affectLi(reason) {
        return (a => (<li className="list-group-item">
            <Affect key={`${a.type} ${a.task} ${a.group_id} ${a.action_id}`} reason={reason} affect={a}/>
            </li>));
    }
    return (<div className="card border-dark m-2 ml-3 mr-3">
        <h5 className="card-header">{action.name}</h5>
        {((action.required.length > 0 || action.excluded.length > 0) && (
        <div className="card-body">
            <Field name="Required Partners" value={action.required.map(r => r.name).join(', ')}/>
            <Field name="Excluded Partners" value={action.excluded.map(r => r.name).join(', ')}/>
        </div>))}
        <ul className="list-group list-group-flush">
            {action.start_affects.map(affectLi("start"))}
            {action.start_emails.map(e => <Email key={e.task + " " + e.name} email={e}/>)}
            {action.complete_affects.map(affectLi("complete"))}
            {action.complete_emails.map(e => <Email key={e.task + " " + e.name} email={e}/>)}
        </ul>
    </div>);
}

function Trigger(props) {
    const trigger = props.trigger;
    return (<li className="list-group-item">
        <Affect reason={trigger.external_action.name + (trigger.external_action.document ? (" - " + trigger.external_action.document.name) : "")} affect={trigger.affect}/>
    </li>);
}

function Group(props) {
    const group = props.group;
    return (<div className="card mb-3">
        <h2 className="card-header">{props.group.name}</h2>
        {((group.required.length > 0 || group.excluded.length > 0) && (<div className="card-body">
            <Field name="Required Partners" value={group.required.map(r => r.name).join(', ')}/>
            <Field name="Excluded Partners" value={group.excluded.map(r => r.name).join(', ')}/>
        </div>))}
        <ul className="list-group list-group-flush">
            <li className="list-group-item list-group-item-info mb-1">Actions</li>
            {props.group.actions.map(a => <Action key={a.action_id} action={a} />)}
        </ul>
        {props.group.triggers.length > 0 && (
            <ul className="list-group list-group-flush">
                <li className="list-group-item list-group-item-info">Triggers</li>
                {props.group.triggers.map(t => <Trigger trigger={t} />)}
            </ul>
        )}
        </div>);
}


function Tree(props) {
    return (<div className="container">
        {props.actionList.groups.map(g => <Group key={g.id} group={g} />)}
    </div>);
}

function attachActionsToAffects(actionList) {
        // Move Default External Triggers from first to last. It's built-in and uninteresting
        actionList.groups.push(actionList.groups.shift());

        const actionLookup = {};
        actionList.groups.forEach(group => {
            const actionById = {};
            actionLookup[group.id] = actionById;
            group.actions.forEach(a => {actionById[a.action_id] = a});
        });
        function attach(item) {
            if (!item.group_id || !item.action_id) {
                return;
            }
            item.action = actionLookup[item.group_id][item.action_id];
        }
        actionList.groups.forEach(group => {
            group.actions.forEach(action =>{
                action.start_affects.forEach(attach);
                action.complete_affects.forEach(attach);
            });
            group.triggers.forEach(trigger =>{ attach(trigger.affect); });
        });
        return actionList;
}

export {Tree, attachActionsToAffects};