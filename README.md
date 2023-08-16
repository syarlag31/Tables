## 🔥 Tables - Social Media Web Application 🔥

Welcome to Tables! Dive into the code to find a fully functional social platform made with Flask and enhanced by YOLOS object detection. Users can create posts, comment, upvote/downvote, and so much more. But beware - the platform has a fun twist with its content management system!

### 🌐 Routes Overview:

1. **Landing Page**: `'/'`
    - This is the main landing page displaying a warm welcome to both guests and logged-in users.

2. **Feed Page**: `'/feed'`
    - The main feed where users can sort and view posts by different criteria like newest, oldest, most karma, etc.

3. **Profile Page**: `'/profile/<string:handle>'`
    - Showcases user profiles with their posts, descriptions, and profile pictures.

4. **Post Management**:
    - Creating a new post: `'/new-post'`
    - Viewing a specific post and its comments: `'/post/<string:post_id>'`
    - Editing a post: `'/post/<string:post_id>/edit-post'`
    - Deleting a post: `'/post/<string:post_id>/delete'`

5. **Comments Management**:
    - Creating a comment: `'/post/<string:post_id>/new-comment'`
    - Editing a comment: `'/post/<string:post_id>/<string:comment_id>/edit-comment'`
    - Deleting a comment: `'/post/<string:post_id>/<string:comment_id>/delete-comment'`

6. **Karma Actions**:
    - Upvoting a post or comment: `'/karma/upvote-karma/<string:user_id>/<string:object_uuid>'`
    - Downvoting a post or comment: `'/karma/downvote-karma/<string:user_id>/<string:object_uuid>'`

7. **User Profile Management**:
    - Adding a profile description: `'/profile/<string:user_id>/add-description'`
    - Editing a profile description: `'/profile/<string:user_id>/edit-description'`
    - Changing profile picture: `'/profile/<string:user_id>/edit-pfp'`

8. **Banned Users Page**: `'/banned/<string:reason>'`
    - Displays a notification for users banned due to certain reasons like posting tables (yes, it's a fun twist!).

### 🤖 Advanced Features:

- **YOLOS Object Detection Integration**: 
    - Before a user post goes live, it's scanned by the YOLOS Object Detection model for certain objects. Posts containing tables are hilariously forbidden!
    
- **File Security**:
    - The app ensures that only allowed file types (png, jpg, jpeg) are uploaded, leveraging `werkzeug.utils.secure_filename`.

- **Async Programming**:
    - Object detection runs asynchronously for non-blocking operations.

### 📚 Dependencies:

- **Flask**: For web application structure and routing.
- **SQLAlchemy**: For database operations.
- **Flask-Login**: To manage user sessions and authentication.
- **Transformers & Torch**: For YOLOS object detection.
- **PIL**: For image processing.

### 🚀 How to Run:

1. Set up your virtual environment and install all required packages.
2. Configure your database (SQLAlchemy).
3. Set up the Flask environment.
4. Run the application.

---

🙏 Thank you for visiting this repository.
