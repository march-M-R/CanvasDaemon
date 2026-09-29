"""Offline regression tests. No real Canvas token or network is used."""
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
os.environ.update(CANVAS_BASE_URL='https://canvas.example.test', CANVAS_TOKEN='test-only', COURSE_ID='123')
import canvas_runtime as runtime
import pull_pages
import push_page
import create_classic_quiz as quiz
import upload_canvas_file as upload
import preview_page_in_canvas as preview
import add_page_to_module as placement
import create_module as modules


class RuntimeTests(unittest.TestCase):
    @patch.object(runtime._requests, 'request')
    def test_authenticated_redirects_disabled_and_timeout(self, request):
        runtime.requests.get('https://canvas.example.test/api/v1/courses/123/pages', headers={'Authorization':'Bearer test-only'}, allow_redirects=True)
        self.assertFalse(request.call_args.kwargs['allow_redirects'])
        self.assertEqual(request.call_args.kwargs['timeout'], (10,60))

    @patch.object(runtime._requests, 'request')
    def test_foreign_origin_refused_before_network(self, request):
        with self.assertRaises(ValueError):
            runtime.requests.get('https://evil.example/next', headers={'Authorization':'Bearer test-only'})
        request.assert_not_called()

    def test_config_validation(self):
        for base in ('http://canvas.example', 'https://canvas.example/path', 'https://user:pass@canvas.example'):
            with self.assertRaises(ValueError):runtime.validate_config(base,'test','123')
        with self.assertRaises(ValueError):runtime.validate_config('https://canvas.example','test','0')
        with self.assertRaises(ValueError):runtime.bound({'course_id':'999','base_url':'https://canvas.example.test'},'https://canvas.example.test','123')

    @patch.object(runtime._requests, 'request')
    def test_importing_connection_script_is_read_only(self, request):
        importlib.reload(importlib.import_module('test_canvas'))
        request.assert_not_called()

    @patch.object(runtime._requests, 'request')
    def test_upload_signed_request_then_scoped_callback(self, request):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'file.txt';path.write_text('hello')
            a=Mock(status_code=302, headers={'Location':'https://canvas.example.test/api/v1/files/7/create_success?uuid=x'})
            b=Mock(status_code=200);b.json.return_value={'id':7}
            request.side_effect=[a,b]
            self.assertEqual(runtime.upload_binary(path,{'upload_url':'https://storage.example/upload','upload_params':{'key':'signed'}},'https://canvas.example.test',{'Authorization':'Bearer test-only'}),{'id':7})
            self.assertNotIn('headers',request.call_args_list[0].kwargs)
            self.assertEqual(request.call_args_list[1].kwargs['headers']['Authorization'],'Bearer test-only')

    @patch.object(runtime._requests, 'request')
    def test_upload_foreign_callback_refused(self, request):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'file.txt';path.write_text('hello')
            request.return_value=Mock(status_code=302,headers={'Location':'https://evil.example/api/v1/files/7/create_success'})
            with self.assertRaises(ValueError):runtime.upload_binary(path,{'upload_url':'https://storage.example/upload','upload_params':{}},'https://canvas.example.test',{'Authorization':'Bearer test-only'})
            self.assertEqual(request.call_count,1)


class PageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.pages=self.root/'pages';self.pages.mkdir();self.file=self.pages/'lesson.html';self.file.write_text('old')
        self.page={'title':'Lesson','url':'lesson','page_id':7,'body':'old','updated_at':'one'}
        self.manifest={'course_id':'123','base_url':'https://canvas.example.test','pages':{'lesson.html':{'title':'Lesson','canvas_url':'lesson','html_file':'pages/lesson.html','body_sha256':runtime.body_hash('old'),'last_canvas_update':'one'}}}
        runtime.save_json(self.root/'manifest.json',self.manifest)
        for module in (pull_pages,push_page):
            for name,value in {'ROOT_DIR':self.root,'PAGES_DIR':self.pages,'BACKUPS_DIR':self.root/'backups','MANIFEST_PATH':self.root/'manifest.json'}.items():
                patcher=patch.object(module,name,value,create=True);patcher.start();self.addCleanup(patcher.stop)

    @patch.object(pull_pages,'get_all_pages')
    @patch.object(pull_pages,'get_page_details')
    def test_pull_protects_unpushed_edits(self, detail, pages):
        self.file.write_text('local edits');pages.return_value=[self.page];detail.return_value=self.page
        with patch.object(sys,'argv',['pull_pages']),self.assertRaisesRegex(ValueError,'Local edits'):pull_pages.main()
        self.assertEqual(self.file.read_text(),'local edits')

    @patch.object(pull_pages,'get_all_pages')
    @patch.object(pull_pages,'get_page_details')
    def test_pull_backup_contains_previous_local_body(self, detail, pages):
        pages.return_value=[self.page];detail.return_value={**self.page,'body':'new'}
        with patch.object(sys,'argv',['pull_pages']):pull_pages.main()
        self.assertEqual(self.file.read_text(),'new')
        self.assertEqual(next((self.root/'backups').glob('*/lesson.html')).read_text(),'old')

    @patch.object(pull_pages,'get_all_pages')
    @patch.object(pull_pages,'get_page_details')
    def test_failed_download_never_partially_overwrites(self, detail, pages):
        pages.return_value=[self.page,{'url':'two'}];detail.side_effect=[{**self.page,'body':'new'},RuntimeError('offline')]
        with patch.object(sys,'argv',['pull_pages']),self.assertRaises(RuntimeError):pull_pages.main()
        self.assertEqual(self.file.read_text(),'old')

    @patch.object(push_page,'get_canvas_page')
    @patch.object(push_page,'update_canvas_page')
    def test_dry_run_never_writes(self, update, get):
        get.return_value=self.page;self.file.write_text('new')
        with patch.object(sys,'argv',['push_page','lesson.html']):push_page.main()
        update.assert_not_called();self.assertFalse((self.root/'backups').exists())

    @patch.object(push_page,'get_canvas_page')
    @patch.object(push_page,'update_canvas_page')
    def test_stale_remote_blocks_apply(self, update,get):
        get.return_value={**self.page,'body':'remote edit'}
        with patch.object(sys,'argv',['push_page','lesson.html','--apply','--confirm-course','123']),self.assertRaisesRegex(ValueError,'Canvas changed'):push_page.main()
        update.assert_not_called()

    @patch.object(push_page,'get_canvas_page')
    @patch.object(push_page,'update_canvas_page')
    def test_push_backup_and_baseline(self, update,get):
        get.return_value=self.page;self.file.write_text('new');update.return_value={**self.page,'body':'new','updated_at':'two'}
        with patch.object(sys,'argv',['push_page','lesson.html','--apply','--confirm-course','123']):push_page.main()
        self.assertEqual(next((self.root/'backups').glob('*/lesson.html')).read_text(),'old')
        self.assertEqual(json.loads((self.root/'manifest.json').read_text())['pages']['lesson.html']['body_sha256'],runtime.body_hash('new'))

    @patch.object(push_page,'get_canvas_page')
    @patch.object(push_page,'update_canvas_page')
    def test_wrong_confirmation_blocks_apply(self, update,get):
        get.return_value=self.page
        with patch.object(sys,'argv',['push_page','lesson.html','--apply','--confirm-course','999']),self.assertRaises(ValueError):push_page.main()
        update.assert_not_called()


class ContentTests(unittest.TestCase):
    def test_invalid_boolean_answer_rejected(self):
        with self.assertRaises(ValueError):quiz.build_answers_for_true_false({'correct':'false'})

    def test_invalid_quiz_rejected_before_create(self):
        bank={'title':'Example','questions':[{'type':'multiple_choice','question_text':'Which?','choices':[{'text':'A','correct':True},{'text':'B','correct':True}]}]}
        with self.assertRaises(ValueError):quiz.validate_quiz_bank(bank)

    @patch.object(quiz,'create_quiz')
    def test_quiz_dry_run(self, create):
        bank={'title':'Example','questions':[{'type':'true_false','question_text':'A claim','correct':False}]}
        with patch.object(quiz,'load_quiz_bank',return_value=bank),patch.object(sys,'argv',['quiz','example.json']):quiz.main()
        create.assert_not_called()

    @patch.object(placement,'canvas_get_all')
    @patch.object(placement.requests,'post')
    def test_repeated_module_attachment_is_noop(self,post,inventory):
        item={'id':1,'type':'Page','page_url':'lesson'};inventory.return_value=[item]
        self.assertEqual(placement.add_page_to_module(3,'Lesson','lesson'),item);post.assert_not_called()

    @patch.object(modules,'list_modules')
    @patch.object(modules.requests,'post')
    def test_existing_module_is_not_recreated(self,post,inventory):
        inventory.return_value=[{'id':3,'name':'Module 1','position':1}]
        with patch.object(sys,'argv',['create_module','module 1','--apply','--confirm-course','123']):modules.main()
        post.assert_not_called()

    @patch.object(modules,'list_modules',return_value=[])
    @patch.object(modules.requests,'post')
    def test_create_module_dry_run_never_writes(self,post,inventory):
        with patch.object(sys,'argv',['create_module','Module 2','--position','2']):modules.main()
        post.assert_not_called()

    @patch.object(modules,'list_modules',return_value=[])
    @patch.object(modules.requests,'post')
    def test_create_module_payload(self,post,inventory):
        response=Mock();response.json.return_value={'id':4,'name':'Module 2','position':2,'published':False};response.links={}
        post.return_value=response
        with patch.object(sys,'argv',['create_module','Module 2','--position','2','--require-sequential-progress','--prerequisite-module-id','1','--apply','--confirm-course','123']):modules.main()
        payload=post.call_args.kwargs['data']
        self.assertEqual(payload['module[name]'],'Module 2')
        self.assertEqual(payload['module[position]'],2)
        self.assertEqual(payload['module[published]'],'false')
        self.assertEqual(payload['module[require_sequential_progress]'],'true')
        self.assertEqual(payload['module[prerequisite_module_ids][]'],['1'])

    @patch.object(preview.requests,'get')
    @patch.object(preview.requests,'put')
    def test_published_preview_is_protected(self,put,get):
        get.return_value.json.return_value={'published':True}
        with self.assertRaises(ValueError):preview.update_preview_page('preview','body')
        put.assert_not_called()


class AdditionalRegressionTests(unittest.TestCase):
    def test_parent_environment_file_is_not_discovered(self):
        with tempfile.TemporaryDirectory() as folder:
            parent=Path(folder);child=parent/'child';child.mkdir()
            (parent/'.env').write_text('CANVAS_TOKEN=parent-token\n')
            with patch.object(runtime,'ROOT',child),patch.dict(os.environ,{},clear=True):
                runtime.load_dotenv()
                self.assertNotIn('CANVAS_TOKEN',os.environ)

    @patch.object(runtime._requests,'request')
    def test_cross_course_pagination_refused(self,request):
        with self.assertRaises(ValueError):
            runtime.requests.get('https://canvas.example.test/api/v1/courses/999/pages',headers={'Authorization':'Bearer test-only'})
        request.assert_not_called()

    @patch.object(runtime._requests,'request')
    def test_download_drops_token_on_storage_redirect(self,request):
        first=Mock(status_code=302,headers={'Location':'https://storage.example/signed'})
        second=Mock(status_code=200,content=b'asset')
        request.side_effect=[first,second]
        self.assertEqual(runtime.download('https://canvas.example.test/files/1/download',{'Authorization':'Bearer test-only'}),b'asset')
        self.assertEqual(request.call_args_list[1].kwargs['headers'],{})

    def test_quiz_settings_omit_implicit_publication_change(self):
        import sync_classic_quiz
        self.assertNotIn('quiz[published]',sync_classic_quiz.build_quiz_payload({'title':'Quiz'}))
        self.assertEqual(sync_classic_quiz.build_quiz_payload({'title':'Quiz','published':False})['quiz[published]'],'false')

    @patch.object(quiz,'add_question',side_effect=RuntimeError('interrupted'))
    @patch.object(quiz,'create_quiz',return_value={'id':9,'title':'Example','published':False})
    def test_partial_quiz_identity_is_saved(self,create,question):
        bank={'title':'Example','questions':[{'type':'true_false','question_text':'Claim','correct':True}]}
        with tempfile.TemporaryDirectory() as folder,patch.object(quiz,'QUIZ_REPORTS_DIR',Path(folder)),patch.object(quiz,'load_quiz_bank',return_value=bank),patch.object(sys,'argv',['quiz','example.json','--apply','--confirm-course','123']):
            with self.assertRaises(RuntimeError):quiz.main()
            data=json.loads((Path(folder)/'created-9.json').read_text())
            self.assertEqual(data['status'],'questions-pending')
            self.assertEqual(data['quiz']['id'],9)

    @patch.object(upload,'start_upload')
    def test_upload_dry_run_does_not_start_transfer(self,start):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'image.png';path.write_bytes(b'example')
            with patch.object(upload,'ASSET_MANIFEST_PATH',Path(folder)/'assets.json'),patch.object(sys,'argv',['upload',str(path)]):upload.main()
            start.assert_not_called()

    @patch.object(pull_pages.requests,'request')
    def test_repeated_pagination_stops(self,request):
        response=Mock();response.json.return_value=[]
        response.links={'next':{'url':'https://canvas.example.test/api/v1/courses/123/pages'}}
        request.return_value=response
        with self.assertRaisesRegex(RuntimeError,'repeated'):pull_pages.get_all_pages()
        self.assertEqual(request.call_count,1)


if __name__=='__main__':unittest.main()
