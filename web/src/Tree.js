import React, { Component } from 'react';

class Col extends Component {
    render() {
        return <div className={"col-" + this.props.width}>{this.props.children}</div>
    }
}

class Row extends Component {
    render() {
        const indent = this.props.indent ? this.props.indent : 0;
        return (<div className="row">
            {this.props.indent && <Col width={indent}/>}
            <Col width={12 - indent}>{this.props.children}</Col>
        </div>);
    }
}

class Email extends Component {
    render() {
        return <Row indent={3}>{this.props.email.name}</Row>;
    }
}

class Affect extends Component {
    render() {
        return <Row indent={3}>{this.props.affect.type} {this.props.affect.action.name}</Row>;
    }
}

class OnDone extends Component {
    render() {
        if (this.props.affects.length === 0 && this.props.emails.length === 0) {
            return null;
        }
        return [<Row indent={2}>On {this.props.task}:</Row>].concat(
            this.props.affects.map(a => <Affect affect={a}/>),
            this.props.emails.map(e => <Email email={e}/>)
        );
    }
}

class ActionDetail extends Component {
    render() {
        return <p>{this.props.action.name}</p>;
    }
}


class Action extends Component {
    render() {
        const action = this.props.action;
        return [<Row indent={1}>{action.name}</Row>,
            <OnDone task="Start" affects={action.start_affects} emails={action.start_emails}/>,
            <OnDone task="Complete" affects={action.complete_affects} emails={action.complete_emails}/>];
    }
}
class Group extends Component {
    render() {
        const groupRow = (<Row>{this.props.group.name}</Row>);
        const actionRows = this.props.group.actions.map(a => <Action action={a}/>);
        return [groupRow].concat(actionRows);
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
        console.log(detailAction);
        return (<div className="container">
            <div className="row">
                <Col width={8}>
                    {this.props.actionList.groups.map(g => <Group group={g}/>)}
                </Col>
                <Col width={4}>
                    <ActionDetail action={detailAction}/>
                </Col>
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