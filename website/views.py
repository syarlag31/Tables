from flask import Blueprint, render_template, request, url_for, redirect, flash, current_app, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import cast, String, UUID
from .models import db, User, Post, Karma, Comment
from werkzeug.utils import secure_filename
import uuid, os, math

from transformers import YolosImageProcessor, YolosForObjectDetection
import torch
from PIL import Image
import asyncio

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

views = Blueprint('views', __name__)

@views.get('/')
def landing():
    return render_template('landing.html', user=current_user)

@views.get('/banned/<string:reason>')
def banned(reason):
    reason = reason
    return render_template('Banned.html', reason=reason, user=current_user)

@views.get('/feed')
@login_required
def feed():
    sort_option = request.args.get('sort', 'select')
    if sort_option == 'oldest':
        posts = Post.query.order_by(Post.timestamp.asc()).all()
    elif sort_option == 'newest':
        posts = Post.query.order_by(Post.timestamp.desc()).all()
    elif sort_option == 'most_karma':
        posts_with_karma = db.session.query(Post).join(Karma, Post.id == cast(Karma.object_uuid, UUID))\
        .filter(Karma.object_type == 'post')\
        .order_by(Karma.karma.desc(), Post.timestamp.desc()).all()

        posts_without_karma = db.session.query(Post).outerjoin(Karma, Post.id == cast(Karma.object_uuid, UUID))\
            .filter(Karma.object_type == None)\
            .order_by(Post.timestamp.desc()).all()

        posts = posts_with_karma + posts_without_karma
    elif sort_option == 'least_karma':
        posts_with_karma = db.session.query(Post).join(Karma, Post.id == cast(Karma.object_uuid, UUID))\
            .filter(Karma.object_type == 'post')\
            .order_by(Karma.karma.asc(), Post.timestamp.asc()).all()

        posts_without_karma = db.session.query(Post).outerjoin(Karma, Post.id == cast(Karma.object_uuid, UUID))\
            .filter(Karma.object_type == None)\
            .order_by(Post.timestamp.asc()).all()

        posts = posts_with_karma + posts_without_karma
    else:
        posts = Post.query.order_by(Post.timestamp.desc()).all()
    num_posts = Post.query.count()
    column_size = math.ceil(num_posts / 3)
    return render_template('Feed.html', user=current_user, posts=posts, num_posts=num_posts, column_size=column_size)

@views.get('/profile/<string:handle>')
@login_required
def profile(handle):
    profile = User.query.filter_by(handle=handle).first()
    user_posts = profile.posts
    num_posts = len(user_posts)
    column_size = math.ceil(num_posts / 3)
    return render_template('Profile.html', profile=profile, user=current_user, num_posts=num_posts, column_size=column_size, user_posts=user_posts)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

async def run_object_detection(image_path):
    image = Image.open(image_path).convert('RGB')
    model = YolosForObjectDetection.from_pretrained('hustvl/yolos-tiny')
    image_processor = YolosImageProcessor.from_pretrained("hustvl/yolos-tiny")

    inputs = image_processor(images=image, return_tensors="pt")
    outputs = model(**inputs)

    # convert outputs (bounding boxes and class logits) to COCO API
    target_sizes = torch.tensor([image.size[::-1]])
    results = image_processor.post_process_object_detection(outputs, threshold=0.5, target_sizes=target_sizes)[0]
        
    detection_dict = {}
    for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
        label_name = model.config.id2label[label.item()]
        confidence = round(score.item(), 3)
        detection_dict[label_name] = confidence
    
    return detection_dict

@views.route('/new-post', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', category='error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', category='error')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            _, ext = os.path.splitext(filename)
            new_filename = f"{uuid.uuid4().hex}{ext}"  # Generate a unique filename
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], new_filename))
            image_url = url_for('static', filename=f'uploads/{new_filename}')

            # Run object detection asynchronously in the background
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            detection_dict = loop.run_until_complete(run_object_detection(os.path.join(current_app.config['UPLOAD_FOLDER'], new_filename)))

            contains_table = any("table" in label or "bench" in label for label in detection_dict.keys())
            contains_chair = 1 if not detection_dict or any("chair" in label for label in detection_dict.keys()) else 0
            
            if contains_table:
                # Delete the user who posted the table
                db.session.delete(current_user)
                db.session.commit()
                flash(f'Illegal Table Post!', category='error')
                return redirect(url_for('views.banned', reason='table'))
            
            post_title = request.form.get('title')
            if not post_title:
                flash('Title is required!', category='error')
                return redirect(request.url)
            
            if current_user.strikes >= 2:
                flash('Your account has been deleted due to three strikes!', category='error')
                db.session.delete(current_user)
                db.session.commit()
                return redirect(url_for('views.banned', reason='strike'))
            
            post = Post(image_url=image_url, user_id=current_user.id, post_title=post_title, contains_chair=contains_chair)
            db.session.add(post)
            db.session.commit()
            flash('Your post has been created!', category='success')
            return redirect(url_for('views.feed'))
        else:
            flash('Allowed file types are png, jpg, jpeg.', category='error')
            return redirect(request.url)

    return render_template('New.html', user=current_user)


@views.get('/post/<string:post_id>')
@login_required
def get_post_by_id(post_id):
    post = Post.query.filter_by(id=post_id).first()
    post_karma = db.session.query(db.func.sum(Karma.karma)).filter_by(object_uuid=post_id).scalar()
    if post_karma is None: post_karma = 0
    comment_karma = {}
    for comment in post.comments:
        comment_karma[comment.id] = db.session.query(db.func.sum(Karma.karma)).filter_by(object_uuid=str(comment.id)).scalar()
        if comment_karma[comment.id] is None:
            comment_karma[comment.id] = 0
    return render_template('Post.html', post=post, user=current_user, post_karma=post_karma, comment_karma=comment_karma)


@views.get('/karma/upvote-karma/<string:user_id>/<string:object_uuid>')
@login_required
def upvote_karma(object_uuid, user_id):
    karma = Karma.query.filter_by(object_uuid=object_uuid, user_id=user_id).first()
    if karma is None:
        if Post.query.filter_by(id=object_uuid).first():
            karma = Karma(karma=1, object_uuid=object_uuid, object_type='post', user_id=current_user.id)
        else:
            comment = Comment.query.filter_by(id=object_uuid).first()
            karma = Karma(karma=1, object_uuid=object_uuid, object_type='comment', user_id=current_user.id)
        db.session.add(karma)
    elif karma.karma == 1 and karma.user_id == current_user.id:
        karma.karma = 0
        db.session.commit()
    else:
        karma.karma = 1
    db.session.commit()
    
    if karma.object_type == 'post':
        return redirect(url_for('views.get_post_by_id', post_id=karma.object_uuid))
    else:
        comment = Comment.query.filter_by(id=karma.object_uuid).first()
        return redirect(url_for('views.get_post_by_id', post_id=comment.post_id))

        
@views.get('/karma/downvote-karma/<string:user_id>/<string:object_uuid>')
@login_required
def downvote_karma(object_uuid, user_id):
    karma = Karma.query.filter_by(object_uuid=object_uuid, user_id=user_id).first()
    if karma is None:
        if Post.query.filter_by(id=object_uuid).first():
            karma = Karma(karma=-1, object_uuid=object_uuid, object_type='post', user_id=current_user.id)
        else:
            comment = Comment.query.filter_by(id=object_uuid).first()
            karma = Karma(karma=-1, object_uuid=object_uuid, object_type='comment', user_id=current_user.id)
        db.session.add(karma)
    elif karma.karma == -1 and karma.user_id == current_user.id:
        karma.karma = 0
        db.session.commit()
    else:
        karma.karma = -1
    db.session.commit()
    
    if karma.object_type == 'post':
        return redirect(url_for('views.get_post_by_id', post_id=karma.object_uuid))
    else:
        comment = Comment.query.filter_by(id=karma.object_uuid).first()
        return redirect(url_for('views.get_post_by_id', post_id=comment.post_id))

@views.route('/post/<string:post_id>/new-comment', methods=['GET', 'POST'])
@login_required
def new_comment(post_id):
    post = Post.query.filter_by(id=post_id).first()
    if request.method == 'POST':
        comment_text = request.form.get('comment_text')
        comment = Comment(text=comment_text, user_id=current_user.id, post_id=post_id)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been added!', category='success')
        return redirect(url_for('views.get_post_by_id', post_id=post_id))
    return render_template('Comment.html', user=current_user, post=post)

@views.post('post/<string:post_id>/delete')
@login_required
def delete_post(post_id):
    post = Post.query.filter_by(id=post_id).first()
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', category='success')
    return redirect(url_for('views.feed'))

@views.post('post/<string:post_id>/<string:comment_id>/delete-comment')
@login_required
def delete_comment(comment_id, post_id):
    comment = Comment.query.filter_by(id=comment_id).first()
    db.session.delete(comment)
    db.session.commit()
    flash('Your comment has been deleted!', category='success')
    return redirect(url_for('views.get_post_by_id', post_id=post_id))

@views.route('/post/<string:post_id>/<string:comment_id>/edit-comment', methods=['GET', 'POST'])
@login_required
def edit_comment(post_id, comment_id):
    comment = Comment.query.filter_by(id=comment_id).first()
    if request.method == 'POST':
        comment_text = request.form.get('comment_text')
        comment.text = comment_text
        db.session.commit()
        flash('Your comment has been updated!', category='success')
        return redirect(url_for('views.get_post_by_id', post_id=post_id))
    return render_template('Edit-Comment.html', user=current_user, post_id=post_id, comment=comment)

@views.route('/post/<string:post_id>/edit-post', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.filter_by(id=post_id).first()
    if request.method == 'POST':
        post_title = request.form.get('post_title')
        post.post_title = post_title
        db.session.commit()
        flash('Your post has been updated!', category='success')
        return redirect(url_for('views.get_post_by_id', post_id=post_id))
    return render_template('Edit-Post.html', user=current_user, post=post)

@views.route('/profile/<string:user_id>/add-description', methods=['GET', 'POST'])
@login_required
def add_description(user_id):
    profile = User.query.filter_by(id=user_id).first()
    if request.method == 'POST':
        description = request.form.get('description')
        profile.description = description
        db.session.commit()
        flash('Your description has been added!', category='success')
        return redirect(url_for('views.profile', handle=profile.handle))
    return render_template('Description.html', user=current_user)

@views.route('/profile/<string:user_id>/edit-description', methods=['GET', 'POST'])
@login_required
def edit_description(user_id):
    profile = User.query.filter_by(id=user_id).first()
    if request.method == 'POST':
        description = request.form.get('description')
        profile.description = description
        db.session.commit()
        flash('Your description has been added!', category='success')
        return redirect(url_for('views.profile', handle=profile.handle))
    return render_template('Edit-Description.html', user=current_user)

@views.route('/profile/<string:user_id>/edit-pfp', methods=['GET', 'POST'])
@login_required
def edit_profile_picture(user_id):
    user = User.query.filter_by(id=user_id).first()
    if request.method == 'POST':
        if 'profile_picture' not in request.files:
            flash('No file part', category='error')
            return redirect(request.url)
        profile_picture = request.files['profile_picture']
        if profile_picture.filename == '':
            flash('No selected file', category='error')
            return redirect(request.url)
        if profile_picture and allowed_file(profile_picture.filename):
            filename = secure_filename(profile_picture.filename)
            _, ext = os.path.splitext(filename)
            new_filename = f"{uuid.uuid4().hex}{ext}"  # Generate a unique filename
            profile_picture.save(os.path.join(current_app.config['UPLOAD_FOLDER'], new_filename))
            image_url = url_for('static', filename=f'uploads/{new_filename}')
            
            # Run object detection asynchronously in the background
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            detection_dict = loop.run_until_complete(run_object_detection(os.path.join(current_app.config['UPLOAD_FOLDER'], new_filename)))

            contains_table = any("table" in label or "bench" in label for label in detection_dict.keys())

            if contains_table:
                # Delete the user who used table image
                db.session.delete(user)
                db.session.commit()
                flash(f'Illegal Profile Picture! Your account has been deleted.', category='error')
                return redirect(url_for('views.banned', reason='table'))
            
            user.pfp_url = image_url
            db.session.commit()
            flash('Your profile picture has been updated!', category='success')
            return redirect(url_for('views.profile', handle=user.handle))
        else:
            flash('Allowed file types are png, jpg, jpeg.', category='error')
            return redirect(request.url)

    return render_template('Edit-PFP.html', user=current_user)