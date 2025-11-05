"""
Unit tests for Comments and Insights functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.facebook_manager import FacebookManager
from src.config import FacebookConfig
from src.models import (
    CommentData,
    CommentsResponse,
    PostInsights,
    PageInsights,
    ReactionBreakdown,
    CommentReplyRequest,
    CommentReactionRequest,
    CommentActionResponse,
    InsightPeriod
)
from src.exceptions import FacebookAPIError


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing"""
    return FacebookConfig(
        facebook_page_id="123456789",
        facebook_access_token="EAAtest123456789012345",
        facebook_api_version="v18.0",
        request_timeout=30,
        max_retries=3
    )


@pytest.fixture
def facebook_manager(mock_config):
    """Create a FacebookManager instance with mock config"""
    return FacebookManager(config=mock_config)


class TestCommentRetrieval:
    """Test comment retrieval functionality"""
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_get_post_comments_success(self, mock_request, facebook_manager):
        """Test successful retrieval of post comments"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [
                {
                    'id': 'comment_1',
                    'message': 'Great post!',
                    'from': {'id': 'user_1', 'name': 'John Doe'},
                    'created_time': '2025-11-03T10:00:00+0000',
                    'like_count': 5
                },
                {
                    'id': 'comment_2',
                    'message': 'Thanks for sharing',
                    'from': {'id': 'user_2', 'name': 'Jane Smith'},
                    'created_time': '2025-11-03T11:00:00+0000',
                    'like_count': 3
                }
            ],
            'paging': {
                'next': 'https://graph.facebook.com/next_page'
            }
        }
        mock_request.return_value = mock_response
        
        comments = facebook_manager.get_post_comments('123456789_987654321')
        
        assert isinstance(comments, CommentsResponse)
        assert len(comments.comments) == 2
        assert all(isinstance(c, CommentData) for c in comments.comments)
        assert comments.comments[0].message == 'Great post!'
        assert comments.comments[0].from_user['name'] == 'John Doe'
        assert comments.comments[1].like_count == 3
        
        # Verify API call
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert '123456789_987654321/comments' in call_args[1]['url']
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_get_post_comments_with_limit(self, mock_request, facebook_manager):
        """Test comment retrieval with limit parameter"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [
                {
                    'id': 'comment_1',
                    'message': 'Test comment',
                    'from': {'id': 'user_1', 'name': 'Test User'},
                    'created_time': '2025-11-03T10:00:00+0000'
                }
            ]
        }
        mock_request.return_value = mock_response
        
        comments = facebook_manager.get_post_comments('123456789_987654321', limit=1)
        
        # Verify limit parameter was passed
        call_args = mock_request.call_args
        assert call_args[1]['params']['limit'] == 1
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_get_post_comments_empty(self, mock_request, facebook_manager):
        """Test retrieval when post has no comments"""
        mock_response = Mock()
        mock_response.json.return_value = {'data': []}
        mock_request.return_value = mock_response
        
        comments = facebook_manager.get_post_comments('123456789_987654321')
        
        assert isinstance(comments, CommentsResponse)
        assert len(comments.comments) == 0


class TestCommentActions:
    """Test comment action functionality"""
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_reply_to_comment_success(self, mock_request, facebook_manager):
        """Test successful comment reply"""
        mock_response = Mock()
        mock_response.json.return_value = {'id': 'reply_comment_123'}
        mock_request.return_value = mock_response
        
        reply_request = CommentReplyRequest(
            comment_id='comment_123',
            message='Thank you for your comment!'
        )
        
        result = facebook_manager.reply_to_comment(reply_request)
        
        assert isinstance(result, CommentActionResponse)
        assert result.success is True
        # The comment_id should be the original comment, not the reply ID
        assert result.comment_id == 'comment_123'
        
        # Verify API call
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'POST'
        assert 'comment_123/comments' in call_args[1]['url']
        assert call_args[1]['data']['message'] == 'Thank you for your comment!'
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_like_comment_success(self, mock_request, facebook_manager):
        """Test successful comment like"""
        mock_response = Mock()
        mock_response.json.return_value = {'success': True}
        mock_request.return_value = mock_response
        
        reaction_request = CommentReactionRequest(
            comment_id='comment_123',
            reaction_type='LIKE'
        )
        
        result = facebook_manager.react_to_comment(reaction_request)
        
        assert isinstance(result, CommentActionResponse)
        assert result.success is True
        
        # Verify API call
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'POST'
        assert 'comment_123/likes' in call_args[1]['url']
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_hide_comment_success(self, mock_request, facebook_manager):
        """Test successful comment hiding"""
        mock_response = Mock()
        mock_response.json.return_value = {'success': True}
        mock_request.return_value = mock_response
        
        result = facebook_manager.hide_comment('comment_123')
        
        assert isinstance(result, CommentActionResponse)
        assert result.success is True
        
        # Verify API call
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'POST'
        assert 'comment_123' in call_args[1]['url']
        assert call_args[1]['data']['is_hidden'] == 'true'
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_delete_comment_success(self, mock_request, facebook_manager):
        """Test successful comment deletion"""
        mock_response = Mock()
        mock_response.json.return_value = {'success': True}
        mock_request.return_value = mock_response
        
        result = facebook_manager.delete_comment('comment_123')
        
        assert isinstance(result, CommentActionResponse)
        assert result.success is True
        
        # Verify API call
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'DELETE'
        assert 'comment_123' in call_args[1]['url']


class TestKeywordExtraction:
    """Test keyword extraction functionality"""
    
    def test_extract_keywords_basic(self, facebook_manager):
        """Test basic keyword extraction"""
        comments = [
            CommentData(
                comment_id='1',
                post_id='post_1',
                message='I love this product! Great quality and amazing service.',
                from_user={'id': 'user1', 'name': 'User 1'},
                created_time='2025-11-03T10:00:00+0000'
            ),
            CommentData(
                comment_id='2',
                post_id='post_1',
                message='The quality is excellent, highly recommend this product.',
                from_user={'id': 'user2', 'name': 'User 2'},
                created_time='2025-11-03T11:00:00+0000'
            )
        ]
        
        keywords = facebook_manager.extract_keywords(comments, top_n=5)
        
        assert isinstance(keywords, list)
        assert len(keywords) <= 5
        # Should include common words like 'product', 'quality'
        keyword_words = [kw['keyword'] for kw in keywords]
        assert 'product' in keyword_words or 'quality' in keyword_words
    
    def test_extract_keywords_empty_comments(self, facebook_manager):
        """Test keyword extraction with no comments"""
        keywords = facebook_manager.extract_keywords([], top_n=5)
        
        assert isinstance(keywords, list)
        assert len(keywords) == 0
    
    def test_extract_keywords_custom_top_n(self, facebook_manager):
        """Test keyword extraction with custom limit"""
        comments = [
            CommentData(
                comment_id='1',
                post_id='post_1',
                message='test word1 word2 word3 word4 word5 word6',
                from_user={'id': 'user1', 'name': 'User 1'},
                created_time='2025-11-03T10:00:00+0000'
            )
        ]
        
        keywords = facebook_manager.extract_keywords(comments, top_n=3)
        
        assert len(keywords) <= 3


class TestPostInsights:
    """Test post insights retrieval"""
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_get_post_insights_24h(self, mock_request, facebook_manager):
        """Test post insights for 24 hour period"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [
                {
                    'name': 'post_impressions',
                    'values': [{'value': 1500}]
                },
                {
                    'name': 'post_reach',
                    'values': [{'value': 1200}]
                }
            ]
        }
        mock_request.return_value = mock_response
        
        insights = facebook_manager.get_post_insights(
            '123456789_987654321',
            period=InsightPeriod.LAST_24_HOURS
        )
        
        assert isinstance(insights, PostInsights)
        assert insights.post_id == '123456789_987654321'
        assert insights.period == InsightPeriod.LAST_24_HOURS
        
        # Verify API call
        call_args = mock_request.call_args
        assert '123456789_987654321/insights' in call_args[1]['url'] or '123456789_987654321' in call_args[1]['url']
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_get_post_insights_7d(self, mock_request, facebook_manager):
        """Test post insights for 7 day period"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [
                {
                    'name': 'post_impressions',
                    'values': [{'value': 10000}]
                }
            ]
        }
        mock_request.return_value = mock_response
        
        insights = facebook_manager.get_post_insights(
            '123456789_987654321',
            period=InsightPeriod.LAST_7_DAYS
        )
        
        assert insights.period == InsightPeriod.LAST_7_DAYS
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_get_post_insights_with_reactions(self, mock_request, facebook_manager):
        """Test post insights including reaction breakdown"""
        # Mock three calls - one for post details, one for insights, one for reactions
        mock_post_response = Mock()
        mock_post_response.json.return_value = {
            'shares': {'count': 25},
            'comments': {'summary': {'total_count': 42}}
        }
        
        mock_insights_response = Mock()
        mock_insights_response.json.return_value = {
            'data': [
                {'name': 'post_impressions', 'values': [{'value': 1500}]},
                {'name': 'post_reach', 'values': [{'value': 1200}]}
            ]
        }
        
        mock_reactions_response = Mock()
        mock_reactions_response.json.return_value = {
            'LIKE': 50,
            'LOVE': 30,
            'WOW': 10,
            'HAHA': 5,
            'SAD': 2,
            'ANGRY': 1
        }
        
        mock_request.side_effect = [mock_post_response, mock_insights_response, mock_reactions_response]
        
        insights = facebook_manager.get_post_insights('123456789_987654321')
        
        assert insights.reactions is not None
        assert isinstance(insights.reactions, ReactionBreakdown)


class TestPageInsights:
    """Test page insights retrieval"""
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_get_page_insights_success(self, mock_request, facebook_manager):
        """Test successful page insights retrieval"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [
                {
                    'name': 'page_impressions',
                    'values': [{'value': 50000}]
                },
                {
                    'name': 'page_impressions_unique',
                    'values': [{'value': 40000}]
                },
                {
                    'name': 'page_engaged_users',
                    'values': [{'value': 5000}]
                },
                {
                    'name': 'page_fans',
                    'values': [{'value': 10000}]
                }
            ]
        }
        mock_request.return_value = mock_response
        
        insights = facebook_manager.get_page_insights(period=InsightPeriod.LAST_24_HOURS)
        
        assert isinstance(insights, PageInsights)
        assert insights.period == InsightPeriod.LAST_24_HOURS
        
        # Verify API call
        call_args = mock_request.call_args
        assert '/insights' in call_args[1]['url']
    
    @patch('src.facebook_manager.requests.Session.request')
    def test_get_page_insights_week(self, mock_request, facebook_manager):
        """Test page insights for week period"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [
                {'name': 'page_impressions', 'values': [{'value': 100000}]}
            ]
        }
        mock_request.return_value = mock_response
        
        insights = facebook_manager.get_page_insights(period=InsightPeriod.LAST_7_DAYS)
        
        assert insights.period == InsightPeriod.LAST_7_DAYS


class TestCommentDataModel:
    """Test CommentData model"""
    
    def test_valid_comment_data(self):
        """Test creating valid comment data"""
        comment = CommentData(
            comment_id='comment_123',
            post_id='post_123',
            message='Great post!',
            from_user={'id': 'user_123', 'name': 'John Doe'},
            created_time='2025-11-03T10:00:00+0000'
        )
        
        assert comment.comment_id == 'comment_123'
        assert comment.message == 'Great post!'
        assert comment.like_count == 0  # Default value
    
    def test_comment_data_with_optional_fields(self):
        """Test comment data with all optional fields"""
        comment = CommentData(
            comment_id='comment_123',
            post_id='post_123',
            message='Great post!',
            from_user={'id': 'user_123', 'name': 'John Doe'},
            created_time='2025-11-03T10:00:00+0000',
            like_count=10,
            comment_count=2,
            parent_comment_id='parent_123'
        )
        
        assert comment.like_count == 10
        assert comment.comment_count == 2
        assert comment.parent_comment_id == 'parent_123'


class TestReactionBreakdown:
    """Test ReactionBreakdown model"""
    
    def test_reaction_breakdown_total(self):
        """Test total calculation in reaction breakdown"""
        reactions = ReactionBreakdown(
            like=50,
            love=30,
            wow=10,
            haha=5,
            sad=2,
            angry=1
        )
        
        assert reactions.computed_total == 98
    
    def test_reaction_breakdown_defaults(self):
        """Test default values in reaction breakdown"""
        reactions = ReactionBreakdown()
        
        assert reactions.like == 0
        assert reactions.love == 0
        assert reactions.computed_total == 0


class TestInsightPeriodEnum:
    """Test InsightPeriod enum"""
    
    def test_period_values(self):
        """Test that period enum has correct values"""
        assert InsightPeriod.LAST_24_HOURS == "day"
        assert InsightPeriod.LAST_7_DAYS == "week"
