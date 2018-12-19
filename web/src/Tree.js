import React, { Component } from 'react';

class Row extends Component {
    render() {
        const indent = this.props.indent ? this.props.indent : 0;
        return (<div className="row">
            {indent > 0 && <div className={"col-" + indent}/>}
            <div className={"col-"+ (12 - indent)}>{this.props.children}</div>
        </div>);
    }
}

class Email extends Component {
    render() {
        return <Row indent={1}>{this.props.email.name}</Row>;
    }
}

class Affect extends Component {
    render() {
        return <Row indent={1}>{this.props.affect.type} {this.props.affect.action.name}</Row>;
    }
}

class OnDone extends Component {
    render() {
        return [<Row>On {this.props.task}:</Row>].concat(
            this.props.affects.map(a => <Affect affect={a}/>),
            this.props.emails.map(e => <Email email={e}/>)
        );
    }
}


class Action extends Component {
    hasContent(affects, emails) {
        return affects.length > 0 || emails.length > 0;
    }

    render() {
        const action = this.props.action;
        let body = null;
        const hasStart = this.hasContent(action.start_affects, action.start_emails);
        const hasComplete = this.hasContent(action.complete_affects, action.complete_emails);
        if (hasStart || hasComplete) {
            body = (<div className="card-body pt-2 pb-2">
                {hasStart && <OnDone task="Start" affects={action.start_affects} emails={action.start_emails}/>}
                {hasComplete && <OnDone task="Complete" affects={action.complete_affects} emails={action.complete_emails}/>}
            </div>);
        }
        return (<div className="card border-dark mb-1">
            <div className="card-header">{action.name}</div>
            {body}
        </div>);
    }
}
class Group extends Component {
    render() {
        return (<div className="card mb-2">
            <div className="card-header">{this.props.group.name}</div>
            <div className="card-body">
                {this.props.group.actions.map(a => <Action action={a}/>)}
            </div>
            </div>);
    }
}

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

class EmailDetail extends Component {
        render() {
            const email = this.props.email;
            return (<div className="card">
                <div className="card-header">Email {email.name}</div>
                <div className="card-body">
                    <Field name="Subject" value={email.subject}/>
                    <Field name="Body" value={email.body}/>
                    <Field name="Attached Documents" value={email.documents.map(d => d.name).join(', ')}/>
                    <Field name="Generated Templates" value={email.templates.map(t => t.name + " of type " + t.document_type.name).join(', ')}/>
                    <Field name="Recipients" value={email.recipients.map(r => r.name).join(', ')}/>
                </div>
            </div>);
        }
}

class ActionDetail extends Component {
    render() {
        return (<div className="card">
            <div className="card-header">{this.props.action.name} Detail</div>
            <div className="card-body">
                {this.props.action.start_emails.map(e => <EmailDetail email={e}/>)}
                {this.props.action.complete_emails.map(e => <EmailDetail email={e}/>)}
            </div>
        </div>);
    }
}

class Tree extends Component {
    render() {
        function hasEverything(email) {
            return email.documents.length && email.templates.length && email.recipients.length;
        }
        let detailAction = null;
        for (let i = 0; i < this.props.actionList.groups.length && detailAction === null; i++) {
            let group = this.props.actionList.groups[i];
            for (let j = 0; j < group.actions.length && detailAction === null; j++) {
                let action = group.actions[j];
                if (action.start_emails.some(hasEverything) || action.complete_emails.some(hasEverything)) {
                    detailAction = action;
                }
            }
        }
        return (<div className="container">
            <div className="row">
                <div className="col-6" style={{height: '100vh', overflow: "auto"}}>
                    {this.props.actionList.groups.map(g => <Group group={g}/>)}
                </div>
                <div className="col">
                    <ActionDetail action={detailAction}/>
                </div>
            </div>
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