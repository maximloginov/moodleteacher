#!/usr/bin/env python3
#
# Example for a complex grading script that utilizes all features of the moodleteacher library.
#
# TODO:
# - Remember last window size on next start

import argparse
import sys
import os
# Allow execution of script from project root, based on the library
# source code
sys.path.append(os.path.realpath('.'))


from moodleteacher.connection import MoodleConnection      # NOQA
from moodleteacher.assignments import MoodleAssignments    # NOQA
from moodleteacher.files import MoodleFile                 # NOQA


def show_preview(display_name, submission):
    # Avoid mandatory loading of wxPython when using overview only
    from moodleteacher.preview import show_preview as mt_show_preview
    if submission.textfield:
        fake_file = MoodleFile.from_local_data(
            name='(Moodle Text Box)',
            content=submission.textfield,
            content_type='text/html')
        submission.files.append(fake_file)
    if not mt_show_preview(display_name, submission.files):
        print("Sorry, preview not possible.")


def handle_submission(submission, old_comments):
    '''
        Handles the teacher action for a single student submission.
    '''
    if submission.is_graded():
        print("Already graded")
        return
    print("#" * 78)
    # Submission has either textfield content or uploaed files, and was not graded so far.
    if submission.is_group_submission():
        group = submission.assignment.course.get_group(submission.groupid)
        if group:
            members = [u.fullname for u in submission.get_group_members()]
            print("Submission {0.id_} by group {1} - {2}".format(submission, group, members))
            display_name = group.fullname
        else:
            print("Submission {0.id_} by unknown group with ID {0.groupid}".format(submission))
            display_name = "Group {0}".format(submission.groupid)
    else:
        user = submission.assignment.course.users[submission.userid]
        print("Submission {0.id_} by {1.fullname} ({1.id_})".format(submission, user))
        display_name = user.fullname
        print("Current grade: {}".format(submission.load_grade()))
    print("Current feedback: {}".format(submission.load_feedback()))

    # Ask user what to do
    inp = 'x'
    while inp != 'g' and inp != '':
        inp = input(
            "Your options: Enter (g)rading. Show (p)review. S(k)ip this submission.\nYour choice [g]:")
        if inp == 'p':
            show_preview(display_name, submission)
        if inp == 'k':
            return
    if assignment.allows_feedback_comment:
        for index, old_comment in enumerate(old_comments):
            print("({}) {}".format(index, old_comment))
        max_index = len(old_comments)
        comment = input("Feedback for student:")
        if comment.isnumeric():
            index = int(comment)
            comment = old_comments[index]
            print(comment)
        else:
            old_comments.append(comment)
    else:
        comment = ""
    grade = input("Grade:")
    if grade != "":
        print("Saving grade '{0}'...".format(float(grade)))
        submission.save_grade(grade, comment)


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.WARN)

    old_comments = []

    # Prepare connection to your Moodle installation.
    # The flag makes sure that the user is asked for credentials, which are then
    # stored in ~/.moodleteacher for the next time.
    conn = MoodleConnection(interactive=True)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o", "--overview", help="No grading, just give an overview.", default=False, action="store_true")
    parser.add_argument(
        "-c", "--courseid", help="Limit to this course ID (check view.php?id=...).", default=[], action='append')
    parser.add_argument("-a", "--assignmentid",
                        help="Limit to this assignment ID (check view.php?id=...).", default=[], action='append')
    parser.add_argument("-u", "--userid",
                        help="Limit to this user ID.", default=[], action='append')
    args = parser.parse_args()

    # Retrieve list of assignments objects.
    print("Fetching list of assignments ...")
    course_filter = [int(courseid) for courseid in args.courseid]
    if course_filter is []:
        course_filter = None
    assignment_filter = [int(assignmentid) for assignmentid in args.assignmentid]
    if assignment_filter is []:
        assignment_filter = None
    assignments = MoodleAssignments(conn, course_filter=course_filter, assignment_filter=assignment_filter)
    print("Done.")

    # Go through assignments, sorted by deadline (oldest first).
    assignments = sorted(assignments, key=lambda x: x.deadline)
    for assignment in assignments:
        if assignment.course.can_grade:
            if args.userid:
                print("Fetching submission from user {}.".format(args.userid))
                sub=assignment.get_user_submission(int(args.userid[0]), must_have_files=True)
                handle_submission(sub, old_comments)
            else:
                print("Fetching submissions from all users ...")
                submissions = assignment.submissions(must_have_files=True)
                print("Done.")
                gradable = [sub for sub in submissions if not sub.is_empty(
                ) and not sub.is_graded()]
                if args.overview:
                    print("{1} gradable submissions: '{0.name}' ({0.id_}) in '{0.course}' ({0.course.id_}), {2}".format(
                        assignment, len(gradable), 'closed' if assignment.deadline_over() else 'open'))
                else:
                    print("Assignment '{0.name}' in '{0.course}', due to {0.deadline}:".format(
                        assignment))
                    if not assignment.deadline_over():
                        print("  Skipping it, still open.".format(
                            assignment))
                        continue
                    for sub in gradable:
                        handle_submission(sub, old_comments)
