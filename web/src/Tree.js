import React, { Component } from 'react';

class Row extends Component {
    render() {
        const indent = this.props.indent ? this.props.indent : 0;
        return (<div className="row">
            {indent && <div className={"col-" + indent}/>}
            <div className={"col-" + (12 - indent)}>{this.props.children}</div>
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
        return <Row indent={3}>{this.props.affect.type}</Row>;
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
        return this.props.actionList.groups.map(g => <Group group={g}/>)
    }
}

export default Tree;