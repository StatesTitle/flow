import React, { Component } from 'react';

class Field extends Component {
    render() {
        if (!this.props.value) {
            return null;
        } else if (this.props.length > 40) {
            return [<p className="font-weight-bold">{this.props.name}</p>, <p>{this.props.value}</p>];
        } else {
            return (<p><span className="font-weight-bold">{this.props.name}: </span>{this.props.value}</p>);
        }
    }
}

class Email extends Component {
    render() {
        const email = this.props.email;
        return (<li className="list-group-item">
            <Field name="Email" value={email.name}/>
            <Field name="Subject" value={email.subject}/>
            <Field name="Body" value={email.body}/>
            <Field name="Attached Documents" value={email.documents.map(d => d.name).join(', ')}/>
            <Field name="Generated Templates" value={email.templates.map(t => t.name + " of type " + t.document_type.name).join(', ')}/>
            <Field name="Recipients" value={email.recipients.map(r => r.name).join(', ')}/>
            </li>);
    }
}

class Affect extends Component {
    render() {
        return <li className="list-group-item">{this.props.affect.type} {this.props.affect.action.name}</li>;
    }
}

class Action extends Component {
    render() {
        const action = this.props.action;
        return (<div className="card border-dark mb-1">
            <div className="card-header">{action.name}</div>
            <ul className="list-group list-group-flush">
                {action.start_affects.map(a => <Affect key={a.type + " " + a.task + " " + a.group_id + " " + a.action_id} affect={a}/>)}
                {action.start_emails.map(e => <Email key={e.task + " " + e.name} email={e}/>)}
                {action.complete_affects.map(a => <Affect key={a.type + " " + a.task + " " + a.group_id + " " + a.action_id} affect={a}/>)}
                {action.complete_emails.map(e => <Email key={e.task + " " + e.name} email={e}/>)}
            </ul>
        </div>);
    }
}

class Group extends Component {
    render() {
        return (<div className="card mb-2">
            <div className="card-header">{this.props.group.name}</div>
            <div className="card-body">
                {this.props.group.actions.map(a => <Action key={a.action_id} action={a} />)}
            </div>
            </div>);
    }
}


class Tree extends Component {
    render() {
        return (<div className="container">
            {this.props.actionList.groups.map(g => <Group key={g.id} group={g} />)}
        </div>);
    }
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